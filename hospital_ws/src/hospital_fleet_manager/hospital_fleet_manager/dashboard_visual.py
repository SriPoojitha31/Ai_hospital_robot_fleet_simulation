#!/usr/bin/env python3
"""
Hospital Fleet Manager - Advanced Visual Dashboard
Real-time fleet monitoring with interactive hospital map and robot tracking
"""

import json
import threading
import time
import math
import os
import sys
from datetime import datetime
from collections import defaultdict

import rclpy
from flask import Flask, render_template_string, jsonify
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from hospital_fleet_manager.scenario_loader import load_scenario

app = Flask(__name__)
VISUAL_SCENARIO = load_scenario()

# Hospital room positions for map visualization (x, y in virtual coordinates)
# Organized as a realistic floor plan blueprint
HOSPITAL_LAYOUT = {
    # ===== ACCESS & LOBBY (Bottom-Left Corner) =====
    'MainLobby': (15, 8),
    'NorthEntrance': (5, 18),
    'SouthEntrance': (5, 2),
    'EmergencyEntry': (25, 5),
    
    # ===== EMERGENCY & CRITICAL CARE WING (Right Side - High Priority) =====
    'ER': (30, 10),
    'Trauma': (35, 10),
    'ICU': (40, 12),
    'PICU': (40, 6),
    'NICU': (40, 2),
    'CCU': (35, 6),
    
    # ===== NURSING STATION & COORDINATION =====
    'NursingStationE': (42, 9),
    
    # ===== MEDICAL WARDS (Left Side - General Care) =====
    'WardA': (8, 15),
    'WardB': (8, 10),
    'WardC': (8, 5),
    'WardD': (3, 12),
    'WardE': (3, 8),
    
    # ===== SURGERY SUITE (Center-Right, Upper) =====
    'OperatingRoom1': (28, 20),
    'OperatingRoom2': (33, 20),
    'OperatingRoom3': (38, 20),
    'Recovery': (42, 18),
    
    # ===== NURSING STATIONS FOR WARDS =====
    'NursingStationN': (13, 18),
    'NursingStationS': (13, 3),
    
    # ===== DIAGNOSTICS & IMAGING (Far Right) =====
    'Lab': (45, 5),
    'Radiology': (45, 10),
    'MRI': (48, 10),
    'Ultrasound': (48, 6),
    'CT': (48, 2),
    
    # ===== SUPPORT SERVICES (Bottom Center) =====
    'Pharmacy': (20, 2),
    'Cafeteria': (3, 2),
    'Supply': (25, 2),
    'Sterilization': (30, 2),
    
    # ===== ADMINISTRATION (Top Left) =====
    'Administration': (10, 22),
    'Morgue': (3, 22),
    'Physical Therapy': (15, 22),
}

# Backward-compatible aliases so robots from different publishers still map correctly.
LOCATION_ALIASES = {
    'Lobby': 'MainLobby',
    'NurseStation': 'NursingStationE',
    'NurseStationN': 'NursingStationN',
    'NurseStationS': 'NursingStationS',
    'NurseStationE': 'NursingStationE',
}

# Multi-floor overlays for the visual map.
FLOOR_ZONES = [
    {
        'id': 'L3',
        'name': 'Level 3 - Surgery & Administration',
        'x': 95,
        'y': 70,
        'width': 710,
        'height': 120,
        'fill': 'rgba(139, 92, 246, 0.10)',
        'stroke': '#7C3AED',
    },
    {
        'id': 'L2',
        'name': 'Level 2 - Wards & Nursing',
        'x': 95,
        'y': 195,
        'width': 710,
        'height': 120,
        'fill': 'rgba(59, 130, 246, 0.10)',
        'stroke': '#2563EB',
    },
    {
        'id': 'L1',
        'name': 'Level 1 - Emergency, Diagnostics & Support',
        'x': 95,
        'y': 320,
        'width': 710,
        'height': 120,
        'fill': 'rgba(16, 185, 129, 0.10)',
        'stroke': '#059669',
    },
]

# Room to floor mapping for labels and metadata.
ROOM_FLOORS = {
    'MainLobby': 'L1',
    'NorthEntrance': 'L1',
    'SouthEntrance': 'L1',
    'EmergencyEntry': 'L1',
    'ER': 'L1',
    'Trauma': 'L1',
    'ICU': 'L2',
    'PICU': 'L2',
    'NICU': 'L2',
    'CCU': 'L2',
    'NursingStationE': 'L2',
    'WardA': 'L2',
    'WardB': 'L2',
    'WardC': 'L2',
    'WardD': 'L2',
    'WardE': 'L2',
    'OperatingRoom1': 'L3',
    'OperatingRoom2': 'L3',
    'OperatingRoom3': 'L3',
    'Recovery': 'L3',
    'NursingStationN': 'L2',
    'NursingStationS': 'L1',
    'Lab': 'L1',
    'Radiology': 'L1',
    'MRI': 'L1',
    'Ultrasound': 'L1',
    'CT': 'L1',
    'Pharmacy': 'L1',
    'Cafeteria': 'L1',
    'Supply': 'L1',
    'Sterilization': 'L1',
    'Administration': 'L3',
    'Morgue': 'L1',
    'Physical Therapy': 'L3',
}

# Robot specialization colors
ROBOT_COLORS = {
    'delivery': '#3B82F6',           # Blue
    'cleaning': '#10B981',           # Green
    'patient_mover': '#EF4444',      # Red
    'lab_courier': '#8B5CF6',        # Purple
    'heavy_supply': '#F59E0B',       # Amber
    'emergency_response': '#DC2626', # Dark Red
    'general': '#6B7280',            # Gray
}

# Room type color coding (for hospital map)
ROOM_TYPE_COLORS = {
    # Emergency & Critical (Red shades)
    'ER': '#FCA5A5', 'Trauma': '#FCA5A5', 'ICU': '#DC2626', 'PICU': '#DC2626',
    'NICU': '#DC2626', 'CCU': '#FCA5A5',
    # Medical Wards (Blue shades)
    'WardA': '#BFDBFE', 'WardB': '#BFDBFE', 'WardC': '#BFDBFE',
    'WardD': '#BFDBFE', 'WardE': '#BFDBFE',
    # Surgery (Orange shades)
    'OperatingRoom1': '#FDBA74', 'OperatingRoom2': '#FDBA74',
    'OperatingRoom3': '#FDBA74', 'Recovery': '#FED7AA',
    # Diagnostics (Yellow shades)
    'Lab': '#FEE08B', 'Radiology': '#FEE08B', 'MRI': '#FCD34D',
    'Ultrasound': '#FEE08B', 'CT': '#FCD34D',
    # Support Services (Green shades)
    'Pharmacy': '#BBEF63', 'Supply': '#BBEF63', 'Sterilization': '#DCFCE7',
    'Cafeteria': '#D1FAE5',
    # Access & Admin (Gray/White shades)
    'MainLobby': '#E5E7EB', 'NorthEntrance': '#F3F4F6', 'SouthEntrance': '#F3F4F6',
    'EmergencyEntry': '#F3F4F6', 'Administration': '#E5E7EB', 'Morgue': '#D1D5DB',
    'Physical Therapy': '#E2E8F0',
    # Nursing Stations (Purple shades)
    'NursingStationN': '#DDD6FE', 'NursingStationS': '#DDD6FE', 'NursingStationE': '#DDD6FE',
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Hospital Robot Fleet - Interactive Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
            color: #f1f5f9;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1800px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #3B82F6;
            padding-bottom: 20px;
        }
        
        .header h1 {
            font-size: 3rem;
            background: linear-gradient(135deg, #3B82F6 0%, #10B981 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 5px;
        }
        
        .header p {
            color: #cbd5e1;
            font-size: 1.1rem;
        }
        
        .timestamp {
            display: inline-block;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid #3B82F6;
            border-radius: 8px;
            padding: 8px 16px;
            margin-top: 10px;
            font-size: 0.9rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(16, 185, 129, 0.1));
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .stat-card:hover {
            border-color: #3B82F6;
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
            transform: translateY(-3px);
        }
        
        .stat-number {
            font-size: 2.2rem;
            font-weight: 700;
            color: #3B82F6;
            margin-bottom: 6px;
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .section {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.8));
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 16px;
            padding: 22px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .section h2 {
            font-size: 1.5rem;
            margin-bottom: 16px;
            color: #e2e8f0;
            border-bottom: 2px solid rgba(59, 130, 246, 0.3);
            padding-bottom: 12px;
        }
        
        .map-container {
            position: relative;
            background: linear-gradient(135deg, #E8F1F8 0%, #D4E6F1 100%);
            border-radius: 12px;
            border: 2px solid #34495E;
            padding: 15px;
            min-height: 600px;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: inset 0 0 10px rgba(52, 73, 94, 0.2);
        }
        
        #hospitalMap {
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
        }
        
        .legend {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            padding: 8px 10px;
            background: rgba(59, 130, 246, 0.1);
            border-radius: 8px;
        }
        
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        
        .robot-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .robot-card {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 10px;
            padding: 12px;
            transition: all 0.2s ease;
        }
        
        .robot-card:hover {
            border-color: #3B82F6;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.2);
        }
        
        .robot-name {
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 6px;
            font-size: 0.9rem;
        }
        
        .robot-type {
            display: inline-block;
            font-size: 0.75rem;
            padding: 3px 8px;
            background: rgba(59, 130, 246, 0.2);
            border-radius: 6px;
            color: #93c5fd;
            margin-bottom: 6px;
        }
        
        .robot-status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8rem;
            margin: 4px 0;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-active {
            background: #10B981;
            box-shadow: 0 0 10px #10B981;
        }
        
        .status-idle {
            background: #6B7280;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .battery-mini {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            margin-top: 6px;
            padding: 6px 8px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
        }
        
        .battery-bar {
            flex: 1;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .battery-fill {
            height: 100%;
            background: linear-gradient(90deg, #10B981, #6EE7B7);
            transition: all 0.3s;
            border-radius: 3px;
        }
        
        .battery-fill.low {
            background: linear-gradient(90deg, #F59E0B, #FBBF24);
        }
        
        .battery-fill.critical {
            background: linear-gradient(90deg, #EF4444, #F87171);
        }
        
        .battery-fill.empty {
            background: linear-gradient(90deg, #DC2626, #EF5350);
        }
        
        .battery-status-icon {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 600;
            background: rgba(59, 130, 246, 0.2);
        }
        
        .battery-status-icon.good {
            background: rgba(16, 185, 129, 0.2);
            color: #6EE7B7;
        }
        
        .battery-status-icon.low {
            background: rgba(245, 158, 11, 0.2);
            color: #FCD34D;
        }
        
        .battery-status-icon.critical {
            background: rgba(220, 38, 38, 0.2);
            color: #FCA5A5;
        }
        
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 25px;
        }
        
        .chart-container {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.8));
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
            min-height: 280px;
        }
        
        .chart-container h3 {
            margin-bottom: 12px;
            color: #e2e8f0;
            font-size: 1rem;
        }
        
        canvas {
            max-height: 240px;
        }
        
        .activity-log {
            max-height: 300px;
            overflow-y: auto;
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.5);
            padding: 12px;
        }
        
        .log-entry {
            padding: 8px;
            border-left: 3px solid #3B82F6;
            margin-bottom: 8px;
            font-size: 0.85rem;
            color: #cbd5e1;
            background: rgba(59, 130, 246, 0.05);
            border-radius: 4px;
        }
        
        .log-time {
            color: #3B82F6;
            font-weight: 600;
            margin-right: 6px;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(30, 41, 59, 0.5);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(59, 130, 246, 0.5);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(59, 130, 246, 0.8);
        }
        
        @media (max-width: 1200px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Hospital Robot Fleet Command Center</h1>
            <p>Real-Time Autonomous Fleet Management & Monitoring</p>
            <div class="timestamp">Last Update: <span id="last-update">loading...</span></div>
        </div>
        
        <!-- Statistics Dashboard -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-robots">-</div>
                <div class="stat-label">Total Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="busy-robots">-</div>
                <div class="stat-label">Robots Active</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="idle-robots">-</div>
                <div class="stat-label">Robots Ready</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avg-battery">-</div>
                <div class="stat-label">Avg Battery</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="total-tasks">-</div>
                <div class="stat-label">Tasks Done</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="pending-tasks">-</div>
                <div class="stat-label">Tasks Pending</div>
            </div>
        </div>
        
        <!-- Main Content Grid -->
        <div class="main-grid">
            <!-- Hospital Map -->
            <div class="section">
                <h2>📍 Hospital Floor Plan & Robot Positions</h2>
                <div class="map-container">
                    <svg id="hospitalMap" width="100%" height="600" viewBox="0 0 900 600" preserveAspectRatio="xMidYMid meet" style="background: linear-gradient(135deg, #E8F1F8 0%, #D4E6F1 100%);">
                        <!-- Blueprint background grid already added by drawHospitalMap -->
                        <!-- Room elements -->
                        <g id="rooms"></g>
                        <!-- Robot markers -->
                        <g id="robots"></g>
                    </svg>
                </div>
                <div class="legend" id="legend"></div>
            </div>
            
            <!-- Robot Status List -->
            <div class="section">
                <h2>🤖 Fleet Status</h2>
                <div class="robot-list" id="robot-list">
                    <div class="log-entry">Loading robots...</div>
                </div>
            </div>
        </div>
        
        <!-- Analytics Charts -->
        <div class="chart-grid">
            <div class="chart-container">
                <h3>📊 Robot Activity</h3>
                <canvas id="statusChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>🎯 Task Priority Distribution</h3>
                <canvas id="priorityChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>🔋 Battery Health</h3>
                <canvas id="batteryChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>🏷️ Robot Specialization</h3>
                <canvas id="specializationChart"></canvas>
            </div>
        </div>
        
        <!-- Activity Log -->
        <div class="section" style="margin-top: 25px;">
            <h2>📋 Recent Activity Log</h2>
            <div class="activity-log" id="activity-log"></div>
        </div>
    </div>
    
    <script>
        const ROBOT_COLORS = {
            'delivery': '#3B82F6',
            'cleaning': '#10B981',
            'patient_mover': '#EF4444',
            'lab_courier': '#8B5CF6',
            'heavy_supply': '#F59E0B',
            'emergency_response': '#DC2626',
            'general': '#6B7280',
        };
        
        let charts = {};
        let mapData = null;
        let roomByName = {};
        let robotTrails = {};
        let robotMotionState = {};
        let mapReady = false;
        let animationLoopStarted = false;
        let lastAnimationTs = null;
        let routePulsePhase = 0;
        const TRANSIT_HUBS = {
            'L1': { x: 790, y: 380 },
            'L2': { x: 790, y: 255 },
            'L3': { x: 790, y: 130 },
        };
        
        function getBatteryColor(battery) {
            if (battery >= 75) return '#27AE60';
            if (battery >= 50) return '#F39C12';
            if (battery >= 25) return '#E74C3C';
            return '#C0392B';
        }

        function ensureMapData() {
            if (mapData) {
                return Promise.resolve(mapData);
            }
            return fetch('/api/map-data')
                .then(r => r.json())
                .then(data => {
                    mapData = data;
                    roomByName = {};
                    (data.rooms || []).forEach(room => {
                        roomByName[room.name] = room;
                    });
                    return mapData;
                });
        }

        function initializeStaticMap(data) {
            if (mapReady) return;
            const svg = document.getElementById('hospitalMap');
            if (!svg) return;
            const roomsGroup = svg.querySelector('#rooms');
            if (!roomsGroup) return;

            roomsGroup.innerHTML = '';

            if (Array.isArray(data.floors)) {
                data.floors.forEach(floor => {
                    const floorGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                    floorGroup.innerHTML = `
                        <rect
                            x="${floor.x}"
                            y="${floor.y}"
                            width="${floor.width}"
                            height="${floor.height}"
                            fill="${floor.fill}"
                            stroke="${floor.stroke}"
                            stroke-width="1.5"
                            rx="12"
                            opacity="0.9"
                        />
                        <text
                            x="${floor.x + 12}"
                            y="${floor.y + 18}"
                            font-size="11"
                            fill="${floor.stroke}"
                            font-weight="700"
                            letter-spacing="0.2"
                        >${floor.name}</text>
                    `;
                    roomsGroup.appendChild(floorGroup);
                });
            }

            (data.rooms || []).forEach(room => {
                const roomColor = room.color || '#BDC3C7';
                const wallColor = '#2C3E50';
                const roomGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                roomGroup.innerHTML = `
                    <rect
                        x="${room.x - 10}"
                        y="${room.y - 10}"
                        width="20"
                        height="20"
                        fill="${roomColor}"
                        stroke="${wallColor}"
                        stroke-width="2"
                        rx="1"
                        opacity="0.82"
                    />
                    <rect
                        x="${room.x - 9}"
                        y="${room.y - 9}"
                        width="18"
                        height="18"
                        fill="none"
                        stroke="${wallColor}"
                        stroke-width="0.5"
                        opacity="0.3"
                        rx="1"
                    />
                    <text
                        x="${room.x}"
                        y="${room.y}"
                        text-anchor="middle"
                        dominant-baseline="middle"
                        font-size="8"
                        fill="#1A252F"
                        font-weight="700"
                        letter-spacing="0.3"
                    >${room.name.substring(0, 5)}</text>
                    <text
                        x="${room.x}"
                        y="${room.y + 24}"
                        text-anchor="middle"
                        font-size="7"
                        fill="#34495E"
                        font-weight="600"
                        opacity="0.7"
                    >${room.floor || ''}</text>
                `;
                roomsGroup.appendChild(roomGroup);
            });

            mapReady = true;
            updateLegend();
        }

        function buildRobotPath(previousState, nextRoom) {
            if (!previousState) return [{ x: nextRoom.x, y: nextRoom.y }];
            const path = [];
            const currentFloor = previousState.floor || nextRoom.floor;
            const targetFloor = nextRoom.floor || currentFloor;
            path.push({ x: previousState.x, y: previousState.y });
            if (currentFloor !== targetFloor && TRANSIT_HUBS[currentFloor] && TRANSIT_HUBS[targetFloor]) {
                path.push({ x: TRANSIT_HUBS[currentFloor].x, y: TRANSIT_HUBS[currentFloor].y });
                path.push({ x: TRANSIT_HUBS[targetFloor].x, y: TRANSIT_HUBS[targetFloor].y });
            }
            path.push({ x: nextRoom.x, y: nextRoom.y });
            return path;
        }

        function resolveRoomName(rawName, aliases) {
            if (!rawName) return '';
            return aliases[rawName] || rawName;
        }

        function parseTaskDestination(taskText, aliases) {
            if (!taskText || typeof taskText !== 'string') return '';
            const match = taskText.match(/\\(([^)]+)->([^)]+)\\)/);
            if (!match) return '';
            const destination = match[2].trim();
            return resolveRoomName(destination, aliases);
        }

        function buildTransitRoutePoints(origin, originFloor, targetRoom) {
            if (!targetRoom) return [];
            const route = [{ x: origin.x, y: origin.y }];
            const startFloor = originFloor || targetRoom.floor || 'L1';
            const endFloor = targetRoom.floor || startFloor;
            if (startFloor !== endFloor && TRANSIT_HUBS[startFloor] && TRANSIT_HUBS[endFloor]) {
                route.push({ x: TRANSIT_HUBS[startFloor].x, y: TRANSIT_HUBS[startFloor].y });
                route.push({ x: TRANSIT_HUBS[endFloor].x, y: TRANSIT_HUBS[endFloor].y });
            }
            route.push({ x: targetRoom.x, y: targetRoom.y });
            return route;
        }

        function syncRobotTargets(robots) {
            if (!mapData) return;
            const aliases = mapData.location_aliases || {};
            const activeIds = new Set();

            Object.entries(robots || {}).forEach(([robotId, status]) => {
                const normalizedLocation = aliases[status.location] || status.location;
                const room = roomByName[normalizedLocation];
                if (!room) return;

                activeIds.add(robotId);
                const existing = robotMotionState[robotId];
                const color = ROBOT_COLORS[status.type] || '#6B7280';
                const battery = Number(status.battery || 100);
                const currentTask = status.current_task || '';
                const destinationName = parseTaskDestination(currentTask, aliases);
                const destinationRoom = roomByName[destinationName] || null;

                if (!existing) {
                    robotMotionState[robotId] = {
                        x: room.x,
                        y: room.y,
                        floor: room.floor || 'L1',
                        location: normalizedLocation,
                        status: status.status || 'idle',
                        type: status.type || 'general',
                        color,
                        battery,
                        currentTask,
                        destinationName,
                        destinationRoom,
                        path: [{ x: room.x, y: room.y }],
                        pathIndex: 0,
                    };
                    robotTrails[robotId] = [{ x: room.x, y: room.y }];
                    return;
                }

                existing.status = status.status || existing.status;
                existing.type = status.type || existing.type;
                existing.color = color;
                existing.battery = battery;
                existing.currentTask = currentTask;
                existing.destinationName = destinationName;
                existing.destinationRoom = destinationRoom;

                if (existing.location !== normalizedLocation) {
                    existing.path = buildRobotPath(existing, room);
                    existing.pathIndex = 1;
                    existing.location = normalizedLocation;
                    existing.floor = room.floor || existing.floor;
                }
            });

            Object.keys(robotMotionState).forEach(robotId => {
                if (!activeIds.has(robotId)) {
                    delete robotMotionState[robotId];
                    delete robotTrails[robotId];
                }
            });
        }

        function stepRobotMotion(deltaSeconds) {
            Object.entries(robotMotionState).forEach(([robotId, state]) => {
                if (!state.path || state.pathIndex >= state.path.length) return;
                const waypoint = state.path[state.pathIndex];
                const dx = waypoint.x - state.x;
                const dy = waypoint.y - state.y;
                const distance = Math.hypot(dx, dy);
                const speed = state.status === 'busy' ? 110 : 65;
                const step = speed * deltaSeconds;

                if (distance <= step || distance < 0.1) {
                    state.x = waypoint.x;
                    state.y = waypoint.y;
                    state.pathIndex += 1;
                } else {
                    state.x += (dx / distance) * step;
                    state.y += (dy / distance) * step;
                }

                if (!robotTrails[robotId]) robotTrails[robotId] = [];
                robotTrails[robotId].push({ x: state.x, y: state.y });
                if (robotTrails[robotId].length > 20) {
                    robotTrails[robotId] = robotTrails[robotId].slice(-20);
                }
            });
        }

        function renderRobotLayer() {
            const svg = document.getElementById('hospitalMap');
            if (!svg) return;
            const robotsGroup = svg.querySelector('#robots');
            if (!robotsGroup) return;

            let markup = '';
            Object.entries(robotMotionState).forEach(([robotId, state]) => {
                const trail = robotTrails[robotId] || [];
                if (state.status === 'busy' && state.destinationRoom) {
                    const routePoints = buildTransitRoutePoints(
                        { x: state.x, y: state.y },
                        state.floor,
                        state.destinationRoom
                    );
                    if (routePoints.length > 1) {
                        const routeText = routePoints.map(p => `${p.x},${p.y}`).join(' ');
                        markup += `
                            <polyline
                                points="${routeText}"
                                fill="none"
                                stroke="${state.color}"
                                stroke-width="1.6"
                                stroke-dasharray="6 5"
                                opacity="0.45"
                            />
                        `;

                        const routeProgress = routePulsePhase % (routePoints.length - 1);
                        const segIndex = Math.floor(routeProgress);
                        const segT = routeProgress - segIndex;
                        const a = routePoints[segIndex];
                        const b = routePoints[Math.min(routePoints.length - 1, segIndex + 1)];
                        const pulseX = a.x + (b.x - a.x) * segT;
                        const pulseY = a.y + (b.y - a.y) * segT;
                        markup += `
                            <circle
                                cx="${pulseX}"
                                cy="${pulseY}"
                                r="3.2"
                                fill="${state.color}"
                                stroke="#ffffff"
                                stroke-width="1"
                                opacity="0.9"
                            />
                        `;
                    }
                }

                if (trail.length > 1) {
                    const points = trail.map(p => `${p.x},${p.y}`).join(' ');
                    markup += `<polyline points="${points}" fill="none" stroke="${state.color}" stroke-width="1.8" opacity="0.35"/>`;
                }

                markup += `
                    <g>
                        <circle cx="${state.x}" cy="${state.y}" r="9" fill="none" stroke="${getBatteryColor(state.battery)}" stroke-width="2" opacity="0.65" />
                        <circle cx="${state.x}" cy="${state.y}" r="6" fill="${state.color}" stroke="#FFFFFF" stroke-width="1.5" opacity="${state.status === 'busy' ? 1 : 0.8}" />
                        ${state.status === 'busy' ? `
                        <circle cx="${state.x}" cy="${state.y}" r="6" fill="none" stroke="${state.color}" stroke-width="1" opacity="0.45">
                            <animate attributeName="r" from="6" to="13" dur="1.5s" repeatCount="indefinite" />
                            <animate attributeName="opacity" from="0.6" to="0" dur="1.5s" repeatCount="indefinite" />
                        </circle>
                        ` : ''}
                        <text x="${state.x + 10}" y="${state.y - 10}" font-size="7" fill="#0f172a" font-weight="700">${robotId}</text>
                        ${state.status === 'busy' && state.destinationName ? `
                        <text x="${state.x + 10}" y="${state.y + 8}" font-size="6.3" fill="#1e293b" font-weight="600">→ ${state.destinationName}</text>
                        ` : ''}
                        <title>${robotId} - ${state.type} - ${state.location} - Battery: ${state.battery.toFixed(1)}%</title>
                    </g>
                `;
            });

            robotsGroup.innerHTML = markup;
        }

        function animationTick(timestamp) {
            if (!lastAnimationTs) lastAnimationTs = timestamp;
            const deltaSeconds = Math.min(0.08, (timestamp - lastAnimationTs) / 1000);
            lastAnimationTs = timestamp;
            routePulsePhase += deltaSeconds * 1.8;

            stepRobotMotion(deltaSeconds);
            renderRobotLayer();
            requestAnimationFrame(animationTick);
        }

        function ensureAnimationLoop() {
            if (animationLoopStarted) return;
            animationLoopStarted = true;
            requestAnimationFrame(animationTick);
        }

        function drawHospitalMap(robots) {
            ensureMapData()
                .then(data => {
                    initializeStaticMap(data);
                    syncRobotTargets(robots || {});
                    ensureAnimationLoop();
                })
                .catch(err => {
                    console.error('❌ Error fetching map data:', err);
                });
        }

        function updateLegend() {
            const legendContainer = document.getElementById('legend');
            legendContainer.innerHTML = '<div style="grid-column: 1/-1; padding: 8px 0; font-weight: 600; color: #cbd5e1; font-size: 0.85rem;">Department Types:</div>';
            
            const deptTypes = {
                'Emergency': '#DC2626',
                'Wards': '#3B82F6',
                'Surgery': '#F59E0B',
                'Diagnostics': '#FCD34D',
                'Support': '#10B981',
                'Nursing': '#8B5CF6',
                'Admin': '#6B7280'
            };
            
            Object.entries(deptTypes).forEach(([type, color]) => {
                const item = document.createElement('div');
                item.className = 'legend-item';
                item.innerHTML = `
                    <div class="legend-dot" style="background: ${color}; opacity: 0.7;"></div>
                    <span>${type}</span>
                `;
                legendContainer.appendChild(item);
            });
            
            const spacer = document.createElement('div');
            spacer.style.gridColumn = '1/-1';
            spacer.style.height = '8px';
            legendContainer.appendChild(spacer);
            
            const batteryTitle = document.createElement('div');
            batteryTitle.style.gridColumn = '1/-1';
            batteryTitle.style.padding = '8px 0';
            batteryTitle.style.fontWeight = '600';
            batteryTitle.style.color = '#cbd5e1';
            batteryTitle.style.fontSize = '0.85rem';
            batteryTitle.textContent = 'Battery Levels:';
            legendContainer.appendChild(batteryTitle);
            
            const batteryLevels = [
                { level: 'Excellent', color: '#10B981', range: '>75%' },
                { level: 'Good', color: '#F59E0B', range: '50-75%' },
                { level: 'Low', color: '#EF4444', range: '25-50%' },
                { level: 'Critical', color: '#DC2626', range: '<25%' }
            ];
            
            batteryLevels.forEach(({ level, color, range }) => {
                const item = document.createElement('div');
                item.className = 'legend-item';
                item.innerHTML = `
                    <div class="legend-dot" style="background: ${color}; opacity: 0.8;"></div>
                    <span>${level} ${range}</span>
                `;
                legendContainer.appendChild(item);
            });

            const motionSpacer = document.createElement('div');
            motionSpacer.style.gridColumn = '1/-1';
            motionSpacer.style.height = '8px';
            legendContainer.appendChild(motionSpacer);

            const motionHint = document.createElement('div');
            motionHint.style.gridColumn = '1/-1';
            motionHint.style.fontSize = '0.82rem';
            motionHint.style.color = '#93c5fd';
            motionHint.textContent = 'Movement sim: robots glide between rooms, use elevator hubs for floor changes, and show dashed live task routes.';
            legendContainer.appendChild(motionHint);
        }
        
        function updateDashboard() {
            console.log('🔄 updateDashboard called at', new Date().toLocaleTimeString());
            
            Promise.all([
                fetch('/api/stats').then(r => r.json()),
                fetch('/api/status').then(r => r.json()),
                fetch('/api/history').then(r => r.json())
            ]).then(([stats, status, history]) => {
                console.log('📊 Stats received:', stats);
                console.log('📋 Status received:', status);
                console.log('📜 History received:', history);
                
                if (!stats.error) {
                    document.getElementById('total-robots').textContent = stats.total_robots;
                    document.getElementById('busy-robots').textContent = stats.busy_robots;
                    document.getElementById('idle-robots').textContent = stats.idle_robots;
                    document.getElementById('avg-battery').textContent = (stats.avg_battery || 0).toFixed(0) + '%';
                    document.getElementById('total-tasks').textContent = stats.total_tasks;
                    document.getElementById('pending-tasks').textContent = stats.pending_tasks;
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    
                    updateCharts(stats);
                } else {
                    console.error('❌ Stats error:', stats.error);
                }
                
                if (!status.error) {
                    if (!status.robots || Object.keys(status.robots).length === 0) {
                        console.warn('⚠️ No robots in status data!');
                    } else {
                        console.log(`✅ Drawing ${Object.keys(status.robots).length} robots`);
                    }
                    drawHospitalMap(status.robots);
                    updateRobotList(status.robots);
                } else {
                    console.error('❌ Status error:', status.error);
                }
                
                if (!history.error) {
                    updateActivityLog(history.history);
                } else {
                    console.error('❌ History error:', history.error);
                }
            }).catch(err => {
                console.error('❌ Dashboard update error:', err);
            });
        }
        
        function updateRobotList(robots) {
            const container = document.getElementById('robot-list');
            container.innerHTML = '';
            
            Object.entries(robots).sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, status]) => {
                const card = document.createElement('div');
                card.className = 'robot-card';
                const statusClass = status.status === 'busy' ? 'status-active' : 'status-idle';
                const battery = status.battery || 100;
                
                let batteryClass = 'good';
                let batteryLabel = '🔋 Full';
                if (battery < 75 && battery >= 50) {
                    batteryClass = 'low';
                    batteryLabel = '⚠️ Moderate';
                } else if (battery < 50 && battery >= 25) {
                    batteryClass = 'low';
                    batteryLabel = '⚠️ Low';
                } else if (battery < 25) {
                    batteryClass = 'critical';
                    batteryLabel = '🔴 Critical';
                }
                
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="robot-name">${name}</div>
                            <div class="robot-type">${status.type || 'general'}</div>
                        </div>
                        <div class="robot-status">
                            <div class="status-indicator ${statusClass}"></div>
                            <span>${status.status || 'idle'}</span>
                        </div>
                    </div>
                    <div class="battery-mini">
                        <div class="battery-bar">
                            <div class="battery-fill ${batteryClass}" style="width: ${battery}%"></div>
                        </div>
                        <span style="min-width: 30px;">${battery.toFixed(0)}%</span>
                    </div>
                    <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 4px; padding: 4px 0;">
                        <span class="battery-status-icon ${batteryClass}">${batteryLabel}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 6px;">
                        📍 ${status.location || 'Unknown'}
                    </div>
                `;
                container.appendChild(card);
            });
        }
        
        function updateActivityLog(history) {
            const container = document.getElementById('activity-log');
            container.innerHTML = '';
            
            if (!history || history.length === 0) {
                container.innerHTML = '<div class="log-entry">No activities yet...</div>';
                return;
            }
            
            history.slice(-15).reverse().forEach(item => {
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.innerHTML = `
                    <span class="log-time">${item.timestamp}</span>
                    ${item.assignment}
                `;
                container.appendChild(entry);
            });
        }
        
        function updateCharts(stats) {
            const ctx1 = document.getElementById('statusChart').getContext('2d');
            if (charts.status) charts.status.destroy();
            charts.status = new Chart(ctx1, {
                type: 'doughnut',
                data: {
                    labels: ['Active', 'Ready'],
                    datasets: [{
                        data: [stats.busy_robots, stats.idle_robots],
                        backgroundColor: ['#3B82F6', '#10B981'],
                        borderColor: ['#1E40AF', '#065F46'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#e2e8f0', font: { weight: 'bold' } }
                        }
                    }
                }
            });
            
            const ctx2 = document.getElementById('priorityChart').getContext('2d');
            if (charts.priority) charts.priority.destroy();
            charts.priority = new Chart(ctx2, {
                type: 'pie',
                data: {
                    labels: ['Critical', 'High', 'Medium', 'Low'],
                    datasets: [{
                        data: [
                            stats.priority_counts?.critical || 0,
                            stats.priority_counts?.high || 0,
                            stats.priority_counts?.medium || 0,
                            stats.priority_counts?.low || 0
                        ],
                        backgroundColor: ['#DC2626', '#F59E0B', '#3B82F6', '#6B7280'],
                        borderColor: ['#7F1D1D', '#78350F', '#1E40AF', '#374151'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#e2e8f0', font: { weight: 'bold' } } }
                    }
                }
            });
            
            const ctx3 = document.getElementById('batteryChart').getContext('2d');
            if (charts.battery) charts.battery.destroy();
            charts.battery = new Chart(ctx3, {
                type: 'bar',
                data: {
                    labels: ['High', 'Medium', 'Low', 'Critical'],
                    datasets: [{
                        label: 'Robot Count',
                        data: [
                            stats.battery_ranges?.high || 0,
                            stats.battery_ranges?.medium || 0,
                            stats.battery_ranges?.low || 0,
                            stats.battery_ranges?.critical || 0
                        ],
                        backgroundColor: ['#10B981', '#F59E0B', '#EF4444', '#7F1D1D'],
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(59, 130, 246, 0.1)' } }
                    }
                }
            });
            
            const ctx4 = document.getElementById('specializationChart').getContext('2d');
            if (charts.specialization) charts.specialization.destroy();
            charts.specialization = new Chart(ctx4, {
                type: 'bar',
                data: {
                    labels: Object.keys(stats.specialization_counts || {}).map(s => s.replace(/_/g, ' ')),
                    datasets: [{
                        label: 'Count',
                        data: Object.values(stats.specialization_counts || {}),
                        backgroundColor: '#3B82F6',
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(59, 130, 246, 0.1)' } }
                    }
                }
            });
        }
        
        // Update dashboard every 2 seconds
        console.log('🚀 Dashboard initialized. Starting update loop...');
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

class AdvancedDashboardNode(Node):
    def __init__(self):
        super().__init__('advanced_dashboard_node')
        self._lock = threading.Lock()
        self.robot_status = {}
        self.task_history = []
        self.last_update = datetime.now()
        self.total_tasks_assigned = 0
        self.pending_tasks = 0

        self.create_subscription(String, 'robot_status', self._status_callback, 10)
        self.create_subscription(String, 'task_assignments', self._assignment_callback, 10)

    def _status_callback(self, msg):
        try:
            status_payload = json.loads(msg.data)
            if not isinstance(status_payload, dict):
                raise ValueError('robot_status payload must be a JSON object')
            with self._lock:
                self.robot_status = status_payload
                self.last_update = datetime.now()
        except json.JSONDecodeError:
            self.get_logger().error('Invalid JSON in robot_status message')
        except ValueError as exc:
            self.get_logger().error(str(exc))

    def _assignment_callback(self, msg):
        try:
            data = json.loads(msg.data) if msg.data.startswith('{') else {'task': msg.data}
            item = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'assignment': data.get('task', msg.data),
                'robot': data.get('robot', 'Unknown'),
                'priority': data.get('priority', 'medium'),
                'generated': data.get('generated', False)
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            item = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'assignment': msg.data,
                'robot': 'Unknown',
                'priority': 'medium',
                'generated': False
            }

        with self._lock:
            self.task_history.append(item)
            self.total_tasks_assigned += 1
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]

    def snapshot(self):
        with self._lock:
            return {
                'robot_status': dict(self.robot_status),
                'task_history': list(self.task_history),
                'last_update': self.last_update,
                'total_tasks_assigned': self.total_tasks_assigned,
                'pending_tasks': self.pending_tasks,
            }


dashboard_node = None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/map-data')
def map_data():
    """Return hospital layout data for map visualization"""
    map_scale = 14
    x_offset = 80
    y_offset = 110
    layout = VISUAL_SCENARIO.get("room_positions", HOSPITAL_LAYOUT)
    room_floors = VISUAL_SCENARIO.get("room_floors", ROOM_FLOORS)
    rooms = []
    for room_name, position in layout.items():
        x, y = position
        rooms.append({
            'name': room_name,
            'x': x * map_scale + x_offset,
            'y': y * map_scale + y_offset,
            'floor': room_floors.get(room_name, 'L1'),
            'color': ROOM_TYPE_COLORS.get(room_name, '#BDC3C7'),
        })
    return {
        'rooms': rooms,
        'floors': FLOOR_ZONES,
        'location_aliases': LOCATION_ALIASES,
    }

@app.route('/api/status')
def status():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    snap = dashboard_node.snapshot()
    return {
        'robots': snap['robot_status'],
        'timestamp': snap['last_update'].strftime('%H:%M:%S')
    }

@app.route('/api/history')
def history():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    snap = dashboard_node.snapshot()
    return {'history': snap['task_history'][-30:]}

@app.route('/api/stats')
def stats():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503

    snap = dashboard_node.snapshot()
    robots = snap['robot_status']
    total_robots = len(robots)
    busy_robots = sum(1 for status in robots.values() if status.get('status') == 'busy')
    idle_robots = total_robots - busy_robots
    
    batteries = [status.get('battery', 100.0) for status in robots.values() if isinstance(status.get('battery'), (int, float))]
    avg_battery = sum(batteries) / len(batteries) if batteries else 0.0
    
    battery_ranges = {
        'high': sum(1 for b in batteries if b >= 75),
        'medium': sum(1 for b in batteries if 50 <= b < 75),
        'low': sum(1 for b in batteries if 25 <= b < 50),
        'critical': sum(1 for b in batteries if b < 25)
    }
    
    specialization_counts = {}
    for status in robots.values():
        spec = status.get('type', 'general')
        specialization_counts[spec] = specialization_counts.get(spec, 0) + 1
    
    priority_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for task in snap['task_history']:
        priority = task.get('priority', 'medium')
        if priority in priority_counts:
            priority_counts[priority] += 1
    
    return {
        'total_robots': total_robots,
        'busy_robots': busy_robots,
        'idle_robots': idle_robots,
        'avg_battery': avg_battery,
        'total_tasks': snap['total_tasks_assigned'],
        'pending_tasks': snap['pending_tasks'],
        'battery_ranges': battery_ranges,
        'specialization_counts': specialization_counts,
        'priority_counts': priority_counts
    }


def ros_thread_main():
    global dashboard_node
    rclpy.init()
    dashboard_node = AdvancedDashboardNode()
    try:
        rclpy.spin(dashboard_node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if dashboard_node is not None:
            dashboard_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main():
    # Allow configurable port via environment and fallback if port busy
    base_port = int(os.environ.get('HOSPITAL_DASHBOARD_PORT', os.environ.get('DASHBOARD_PORT', '5000')))
    port = base_port

    thread = threading.Thread(target=ros_thread_main, daemon=True)
    thread.start()
    time.sleep(2)

    # Probe port availability with a test socket before starting Flask
    import socket
    for attempt in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('0.0.0.0', port))
            s.close()
            print(f"\n🌐 Dashboard running at http://localhost:{port}", flush=True)
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
            break
        except OSError:
            print(f"Port {port} is in use, trying next port...", flush=True)
            port += 1
            s.close()
            continue


if __name__ == '__main__':
    main()
