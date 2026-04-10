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
from rclpy.node import Node
from std_msgs.msg import String

app = Flask(__name__)

# Hospital room positions for map visualization (x, y in virtual coordinates)
HOSPITAL_LAYOUT = {
    # Main Lobby & Access
    'MainLobby': (10, 10),
    'NorthEntrance': (10, 20),
    'SouthEntrance': (10, 0),
    'EmergencyEntry': (20, 10),
    
    # Emergency & Critical Care
    'ER': (25, 15),
    'Trauma': (30, 15),
    'ICU': (35, 15),
    'PICU': (35, 20),
    'NICU': (35, 10),
    'CCU': (30, 10),
    
    # Medical Wards
    'WardA': (5, 15),
    'WardB': (5, 10),
    'WardC': (5, 5),
    'WardD': (0, 10),
    'WardE': (0, 5),
    
    # Surgery & Procedure Rooms
    'OperatingRoom1': (20, 25),
    'OperatingRoom2': (25, 25),
    'OperatingRoom3': (30, 25),
    'Recovery': (35, 25),
    
    # Diagnostics & Imaging
    'Lab': (40, 5),
    'Radiology': (40, 15),
    'MRI': (45, 15),
    'Ultrasound': (45, 10),
    'CT': (45, 5),
    
    # Support Services
    'Pharmacy': (15, 0),
    'Cafeteria': (0, 0),
    'Supply': (20, 0),
    'Sterilization': (25, 3),
    
    # Administration & Specialized
    'Administration': (12, 20),
    'Morgue': (8, 22),
    'Physical Therapy': (2, 22),
    
    # Nursing Stations
    'NursingStationN': (18, 20),
    'NursingStationS': (18, 5),
    'NursingStationE': (40, 20),
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
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.9));
            border-radius: 12px;
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 15px;
            min-height: 600px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        #hospitalMap {
            filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.3));
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
                    <svg id="hospitalMap" width="100%" height="600" viewBox="0 0 600 600" style="background: radial-gradient(circle at center, rgba(59, 130, 246, 0.05), transparent);">
                        <!-- Grid lines for reference -->
                        <defs>
                            <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                                <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(59, 130, 246, 0.1)" stroke-width="0.5"/>
                            </pattern>
                        </defs>
                        <rect width="600" height="600" fill="url(#grid)"/>
                        <!-- Rooms will be drawn here dynamically -->
                        <g id="rooms"></g>
                        <!-- Robots will be drawn here dynamically -->
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
        let robotTrails = {};
        
const ROOM_TYPE_COLORS = {
            'ER': '#FCA5A5', 'Trauma': '#FCA5A5', 'ICU': '#DC2626', 'PICU': '#DC2626',
            'NICU': '#DC2626', 'CCU': '#FCA5A5',
            'WardA': '#BFDBFE', 'WardB': '#BFDBFE', 'WardC': '#BFDBFE',
            'WardD': '#BFDBFE', 'WardE': '#BFDBFE',
            'OperatingRoom1': '#FDBA74', 'OperatingRoom2': '#FDBA74',
            'OperatingRoom3': '#FDBA74', 'Recovery': '#FED7AA',
            'Lab': '#FEE08B', 'Radiology': '#FEE08B', 'MRI': '#FCD34D',
            'Ultrasound': '#FEE08B', 'CT': '#FCD34D',
            'Pharmacy': '#BBEF63', 'Supply': '#BBEF63', 'Sterilization': '#DCFCE7',
            'Cafeteria': '#D1FAE5',
            'MainLobby': '#E5E7EB', 'NorthEntrance': '#F3F4F6', 'SouthEntrance': '#F3F4F6',
            'EmergencyEntry': '#F3F4F6', 'Administration': '#E5E7EB', 'Morgue': '#D1D5DB',
            'PhysicalTherapy': '#E2E8F0',
            'NursingStationN': '#DDD6FE', 'NursingStationS': '#DDD6FE', 'NursingStationE': '#DDD6FE',
        };

        function getDepartmentType(roomName) {
            if (roomName.includes('ER') || roomName.includes('Trauma') || roomName.includes('ICU') || roomName.includes('PICU') || roomName.includes('NICU') || roomName.includes('CCU')) return 'Emergency';
            if (roomName.includes('Ward')) return 'Wards';
            if (roomName.includes('Operating') || roomName.includes('Recovery')) return 'Surgery';
            if (roomName.includes('Lab') || roomName.includes('Radiology') || roomName.includes('MRI') || roomName.includes('Ultrasound') || roomName.includes('CT')) return 'Diagnostics';
            if (roomName.includes('Pharmacy') || roomName.includes('Supply') || roomName.includes('Sterilization') || roomName.includes('Cafeteria')) return 'Support';
            if (roomName.includes('Nursing')) return 'Nursing';
            return 'Admin';
        }

        function drawHospitalMap(robots) {
            const svg = document.getElementById('hospitalMap');
            const roomsGroup = svg.querySelector('#rooms');
            const robotsGroup = svg.querySelector('#robots');
            
            // Clear previous content
            roomsGroup.innerHTML = '';
            robotsGroup.innerHTML = '';
            
            // Fetch room data from server
            fetch('/api/map-data')
                .then(r => r.json())
                .then(data => {
                    if (!data.error) {
                        // Draw rooms with color coding
                        data.rooms.forEach((room, idx) => {
                            const roomColor = ROOM_TYPE_COLORS[room.name] || 'rgba(59, 130, 246, 0.15)';
                            const roomGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                            roomGroup.innerHTML = `
                                <defs>
                                    <filter id="drop-shadow-${idx}" x="-50%" y="-50%" width="200%" height="200%">
                                        <feDropShadow dx="2" dy="2" stdDeviation="2" flood-opacity="0.3"/>
                                    </filter>
                                </defs>
                                <rect 
                                    x="${room.x - 8}" 
                                    y="${room.y - 8}" 
                                    width="16" 
                                    height="16"
                                    fill="${roomColor}"
                                    stroke="#334155"
                                    stroke-width="1.5"
                                    rx="2"
                                    filter="url(#drop-shadow-${idx})"
                                    opacity="0.85"
                                />
                                <text 
                                    x="${room.x}" 
                                    y="${room.y + 22}" 
                                    text-anchor="middle"
                                    font-size="9"
                                    fill="#cbd5e1"
                                    font-weight="600"
                                    letter-spacing="0.5"
                                >${room.name.substring(0, 6)}</text>
                            `;
                            roomsGroup.appendChild(roomGroup);
                        });
                        
                        // Draw robots with enhanced visualization
                        Object.entries(robots).forEach(([robotId, status]) => {
                            const room = data.rooms.find(r => r.name === status.location);
                            if (room) {
                                const color = ROBOT_COLORS[status.type] || '#6B7280';
                                const battery = status.battery || 100;
                                const getBatteryColor = (bat) => {
                                    if (bat >= 75) return '#10B981';
                                    if (bat >= 50) return '#F59E0B';
                                    if (bat >= 25) return '#EF4444';
                                    return '#DC2626';
                                };
                                
                                const robotGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                                robotGroup.innerHTML = `
                                    <!-- Battery ring indicator -->
                                    <circle 
                                        cx="${room.x}" 
                                        cy="${room.y}" 
                                        r="8"
                                        fill="none"
                                        stroke="${getBatteryColor(battery)}"
                                        stroke-width="1.5"
                                        opacity="0.6"
                                    />
                                    <!-- Main robot circle -->
                                    <circle 
                                        cx="${room.x}" 
                                        cy="${room.y}" 
                                        r="5"
                                        fill="${color}"
                                        stroke="white"
                                        stroke-width="1.5"
                                        opacity="${status.status === 'busy' ? 1 : 0.7}"
                                    />
                                    <!-- Pulsing animation ring for active robots -->
                                    ${status.status === 'busy' ? `
                                    <circle 
                                        cx="${room.x}" 
                                        cy="${room.y}" 
                                        r="5"
                                        fill="none"
                                        stroke="${color}"
                                        stroke-width="0.8"
                                        opacity="0.5"
                                    >
                                        <animate 
                                            attributeName="r" 
                                            from="5" 
                                            to="11" 
                                            dur="1.5s" 
                                            repeatCount="indefinite"
                                        />
                                        <animate 
                                            attributeName="opacity" 
                                            from="0.5" 
                                            to="0" 
                                            dur="1.5s" 
                                            repeatCount="indefinite"
                                        />
                                    </circle>
                                    ` : ''}
                                    <title>${robotId} - ${status.type} - Battery: ${battery.toFixed(0)}% - ${status.status} (${status.location})</title>
                                `;
                                robotsGroup.appendChild(robotGroup);
                            }
                        });
                        
                        // Update legend
                        updateLegend();
                    }
                })
                .catch(console.error);
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
        }
        
        function updateDashboard() {
            Promise.all([
                fetch('/api/stats').then(r => r.json()),
                fetch('/api/status').then(r => r.json()),
                fetch('/api/history').then(r => r.json())
            ]).then(([stats, status, history]) => {
                if (!stats.error) {
                    document.getElementById('total-robots').textContent = stats.total_robots;
                    document.getElementById('busy-robots').textContent = stats.busy_robots;
                    document.getElementById('idle-robots').textContent = stats.idle_robots;
                    document.getElementById('avg-battery').textContent = (stats.avg_battery || 0).toFixed(0) + '%';
                    document.getElementById('total-tasks').textContent = stats.total_tasks;
                    document.getElementById('pending-tasks').textContent = stats.pending_tasks;
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    
                    updateCharts(stats);
                }
                
                if (!status.error) {
                    drawHospitalMap(status.robots);
                    updateRobotList(status.robots);
                }
                
                if (!history.error) {
                    updateActivityLog(history.history);
                }
            }).catch(console.error);
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
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

class AdvancedDashboardNode(Node):
    def __init__(self):
        super().__init__('advanced_dashboard_node')
        self.robot_status = {}
        self.task_history = []
        self.last_update = datetime.now()
        self.total_tasks_assigned = 0
        self.pending_tasks = 0

        self.create_subscription(String, 'robot_status', self._status_callback, 10)
        self.create_subscription(String, 'task_assignments', self._assignment_callback, 10)

    def _status_callback(self, msg):
        try:
            self.robot_status = json.loads(msg.data)
            self.last_update = datetime.now()
        except json.JSONDecodeError:
            self.get_logger().error('Invalid JSON in robot_status message')

    def _assignment_callback(self, msg):
        try:
            data = json.loads(msg.data) if msg.data.startswith('{') else {'task': msg.data}
            self.task_history.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'assignment': data.get('task', msg.data),
                'robot': data.get('robot', 'Unknown'),
                'priority': data.get('priority', 'medium'),
                'generated': data.get('generated', False)
            })
            self.total_tasks_assigned += 1
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]
        except:
            self.task_history.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'assignment': msg.data,
                'robot': 'Unknown',
                'priority': 'medium',
                'generated': False
            })


dashboard_node = None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/map-data')
def map_data():
    """Return hospital layout data for map visualization"""
    rooms = []
    for room_name, (x, y) in HOSPITAL_LAYOUT.items():
        rooms.append({
            'name': room_name,
            'x': x * 12,  # Scale up for SVG
            'y': y * 12
        })
    return {'rooms': rooms}

@app.route('/api/status')
def status():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    return {
        'robots': dashboard_node.robot_status,
        'timestamp': dashboard_node.last_update.strftime('%H:%M:%S')
    }

@app.route('/api/history')
def history():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    return {'history': dashboard_node.task_history[-30:]}

@app.route('/api/stats')
def stats():
    if dashboard_node is None:
        return {'error': 'Dashboard not initialized'}, 503
    
    robots = dashboard_node.robot_status
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
    for task in dashboard_node.task_history:
        priority = task.get('priority', 'medium')
        if priority in priority_counts:
            priority_counts[priority] += 1
    
    return {
        'total_robots': total_robots,
        'busy_robots': busy_robots,
        'idle_robots': idle_robots,
        'avg_battery': avg_battery,
        'total_tasks': dashboard_node.total_tasks_assigned,
        'pending_tasks': dashboard_node.pending_tasks,
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
    except KeyboardInterrupt:
        pass
    finally:
        dashboard_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    
    thread = threading.Thread(target=ros_thread_main, daemon=True)
    thread.start()
    time.sleep(2)
    
    print(f"\n🌐 Dashboard running at http://localhost:{port}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
