Gazebo / gz (gz-sim) setup notes
=================================

Recommended (apt) packages for ROS 2 Jazzy + gz-sim

- Install the distro packages (preferred over Snap):

```bash
sudo apt update
sudo apt install -y ros-jazzy-gz-sim ros-jazzy-ros-gz
```

- If you have a `gz` binary from Snap, remove it to avoid GLIBC / library conflicts:

```bash
sudo snap remove gz || true
```

Verify the `gz` binary is the apt one:

```bash
command -v gz
readlink -f $(command -v gz)
# path should point under /usr/bin or /opt/ros/jazzy, not /snap/
```

Notes for this project

- This repository packages model files from `src/hospital_fleet_manager/hospital_fleet_manager/models/` during a proper `colcon build` / install. Do not rely on manual copies left under `install/` in the repository — run `colcon build` to regenerate the `install/` layout.
- If Gazebo reports missing plugins, ensure the installed gz-sim package version matches the plugin names used in the model SDFs (this repo uses `libgz-sim8-*` filenames and `gz::sim::systems::...` aliases compatible with the apt packages).

Troubleshooting

- If you see errors referencing `/snap/` libraries (GLIBC_PRIVATE, libpthread), remove the snap `gz` and install the apt packages above.
- To inspect available gz-sim plugins:

```bash
ls -la /opt/ros/jazzy/opt/gz_sim_vendor/lib/gz-sim-8/plugins/
strings /opt/ros/jazzy/opt/gz_sim_vendor/lib/gz-sim-8/plugins/libgz-sim8-diff-drive-system.so | head -n 40
```

If you want, I can add these instructions to the top-level README instead.
