# 🎁 Blendpack

**Pack all your Blender assets into one portable package for easy sharing – no more missing files!**

Blendpack is a powerful Blender addon that automatically collects all external assets (textures, sounds, VDBs, HDRIs, sequences, libraries, and more) from your Blender project, organizes them into a clean folder structure, relinks all paths to be relative and portable, and packages everything into a single ZIP archive.

---

## 📸 Preview
<p align="center">
<img width="316" height="451" alt="Screenshot 2025-11-16 170858" src="https://github.com/user-attachments/assets/4eabc9b6-2a99-4b43-898e-8d4f000e7f34" />
</p>


---

## 📦 Download
<a href="https://github.com/MeRahulAhire/BlendPack/raw/refs/heads/master/BlendPack.zip">
    <img src="https://img.shields.io/badge/Download-Blendpack%20v1.0-blue?style=for-the-badge&logo=blender&logoColor=white" alt="Download Blendpack">
</a>

---

## ✨ Features

### 📦 Comprehensive Asset Collection
Blendpack automatically detects and collects:

- **Images & Textures** – All image files used in materials, shaders, and compositing
- **Video Textures** – MP4, AVI, MOV, MKV, and other video formats used as textures
- **Image Sequences** – Automatically detects and collects entire frame sequences
- **HDRIs** – HDR and EXR environment maps
- **Sounds** – Audio files from the Video Sequencer and speaker objects
- **Fonts** – Custom fonts used in text objects
- **VDB Volumes** – OpenVDB files including sequences
- **Linked Libraries** – External .blend files
- **Cache Files** – Alembic (.abc) and USD (.usd/.usda/.usdc) files
- **Scripts** – Python scripts referenced in shader/geometry nodes
- **IES Lights** – IES light profiles
- **Packed Files** – Automatically extracts and includes packed data

### 🚀 High-Performance Compression
- **7-Zip Integration** – Uses native 7-Zip binaries for **5-10x faster** compression than standard Python
- **Multi-threaded** – Takes advantage of all CPU cores for maximum speed
- **Real-time Progress** – Live progress tracking with percentage updates
- **Smart Fallback** – Automatically falls back to Python's zipfile if 7-Zip isn't available
- **Cross-Platform** – Works on Windows (x64/ARM64), Linux (x64/ARM64), and macOS (Universal)

### 📁 Intelligent Organization
- **Category-based Folders** – Assets organized by type (textures, sounds, vdbs, etc.)
- **Subdirectory Preservation** – Maintains partial folder structure to avoid conflicts
- **Name Conflict Resolution** – Automatically handles duplicate filenames
- **Relative Path Relinking** – All paths converted to relative for true portability

### 🔄 Automated Workflow
1. **Collect** – Scans entire project for external references
2. **Copy** – Copies all external files to organized folders
3. **Extract** – Unpacks any packed files into the asset folders
4. **Relink** – Creates a modified .blend file with all paths relinked
5. **Verify** – Validates the packed project structure
6. **Archive** – Compresses everything into a single ZIP file
7. **Cleanup** – Removes temporary files

---

## 📥 Installation

### Prerequisites
- Blender 4.0 or newer

### Install Steps
1. Download the latest `blendpack.zip` from releases
2. Open Blender → Edit → Preferences → Add-ons
3. Click "Install..." and select the downloaded ZIP
4. Enable "Blendpack" in the add-ons list
5. The panel appears in the 3D Viewport sidebar (press `N` → Blendpack tab)

---

## 🎮 Usage

### Basic Workflow

1. **Open your Blender project** that you want to pack
2. **Save your .blend file** first (required)
3. **Open the Blendpack panel** in the 3D Viewport sidebar (press `N` key)
4. **Select an output folder** where the packed ZIP will be created
5. **Click "Start Packing"**
6. **Wait for completion** – progress bar shows real-time status
7. **Share the ZIP!** – Everything is now portable and self-contained

### Output Structure

After packing, you'll get a ZIP file containing:
```
project_name_blendpack.zip
├── project_name_clone.blend    ← Modified blend file with relinked paths
└── assets/
    ├── textures/               ← Image textures
    ├── videos/                 ← Video textures
    ├── hdris/                  ← HDR/EXR environment maps
    ├── sounds/                 ← Audio files
    ├── fonts/                  ← Custom fonts
    ├── vdbs/                   ← VDB volume files
    ├── image_sequences/        ← Frame sequences
    ├── libraries/              ← Linked .blend files
    ├── alembic/                ← Alembic cache files
    ├── usd/                    ← USD files
    ├── caches/                 ← Other cache files
    ├── scripts/                ← Python scripts
    ├── ies/                    ← IES light profiles
    └── texts/                  ← Text datablocks
```

### Using the Packed Project

1. **Extract the ZIP** anywhere on any computer
2. **Open `project_name_clone.blend`**
3. **All assets load automatically** – paths are relative and portable!

---

## 🔧 Technical Details

### Supported File Types

| Category | Extensions |
|----------|------------|
| **Images** | .png, .jpg, .jpeg, .tga, .bmp, .tif, .tiff, .exr, .hdr, .dds |
| **Videos** | .mp4, .avi, .mov, .mkv, .webm, .flv, .wmv, .m4v, .mpg, .mpeg |
| **Sounds** | .wav, .mp3, .ogg, .flac, .aac, .wma |
| **Volumes** | .vdb |
| **Caches** | .abc (Alembic), .usd, .usda, .usdc, .usdz (USD) |
| **Fonts** | .ttf, .otf, .woff |
| **Scripts** | .py |
| **Lights** | .ies |
| **Libraries** | .blend |

### Platform Support

| Platform | Architecture | Binary | Status |
|----------|-------------|--------|--------|
| **Windows** | x64 | 7za.exe | ✅ Fully supported |
| **Windows** | ARM64 | 7za.exe | ✅ Fully supported |
| **Linux** | x64 | 7zz | ✅ Fully supported |
| **Linux** | ARM64 | 7zz | ✅ Fully supported |
| **macOS** | Universal (Intel + Apple Silicon) | 7zz | ✅ Fully supported |

*Unsupported architectures automatically fall back to Python's zipfile*

### Path Relinking

Blendpack uses a sophisticated relinking system:

1. **Path Analysis** – Detects both absolute and relative paths
2. **Mapping Creation** – Builds a comprehensive path translation table
3. **Blender Subprocess** – Runs Blender in background to relink paths
4. **Multiple Strategies** – Uses fallback matching for maximum compatibility
5. **Verification** – Validates all relinked paths

All paths are converted to relative (`//assets/...`) for true portability across different computers and operating systems.

---

## 🐛 Troubleshooting

### "Save blend file first" Error
**Solution:** Save your .blend file before packing. Blendpack needs to know where your project is located.

### "Select valid output folder" Error
**Solution:** Click "Select Folder" and choose where you want the ZIP file created.

### Missing Files Warning
**Solution:** Check the console (Window → Toggle System Console) for a list of missing files. Fix the paths in your project and try again.

### 7-Zip Not Working
**Symptom:** Console shows "Falling back to Python zipfile"  
**Solution:** This is normal on unsupported architectures. The addon will still work, just slower.

### Progress Bar Stuck
**Solution:** Check the console for error messages. The process might still be running. Wait a few more seconds.

### Relinked Paths Not Working
**Solution:** Make sure you're opening the `_clone.blend` file from inside the extracted folder, not the original blend file.

---

## 📊 Console Output

Blendpack provides detailed console output for debugging in **Window** > **Toggle System Console** :
```
============================================================
BLENDPACK v2.1 - STARTING
============================================================
Blend: C:\Projects\my_project.blend
Output: C:\Output\

============================================================
COLLECTING ALL ASSETS
============================================================

[Images]
  ✓ textures: brick_color.png
  ✓ textures: brick_normal.png
  🎥 Video texture: explosion.mp4

[Volumes (VDB)]
  📹 Sequence: smoke_####.vdb (240 frames)

[7-Zip] Detected: windows / x64
[7-Zip] Binary found: ...\7za.exe

[  5.0%] Setting up project...
[ 10.0%] Copying assets...
[ 45.0%] Extracting packed files...
[ 60.0%] Creating portable blend...
[ 85.0%] Verifying...
[ 90.0%] Creating archive...
[7-Zip] Running: 7za.exe a -tzip ...
✓ 7-Zip compression successful!
  Archive size: 847.32 MB
[ 95.0%] Cleaning up...
[100.0%] Complete!
```

---

## 🤝 Credits

**Created by Rahul Ahire for Cloud Blender Render**

Get high-performance cloud rendering with RTX 5090 for just $0.69/hour!  
🌐 [cloud-blender-render.rahulahire.com](https://cloud-blender-render.rahulahire.com/)

### Built With
- **7-Zip** – High-performance compression (LGPL license)
- **Blender API** – Python integration for asset management
- **Python** – Core scripting and automation

---

## 📜 License

This addon is provided under GPL license to use with Blender.

7-Zip binaries are distributed under the LGPL license.  
See [7-zip.org/license.txt](https://www.7-zip.org/license.txt) for details.

---

## 💬 Support

**Found a bug?** Open an issue on GitHub with:
- Blender version
- Operating system
- Console output
- Steps to reproduce

**Need help?** Check the console output first – it usually shows what went wrong! You can also email me at info@rahulahire.com

---

## ⭐ Show Your Support

If Blendpack saved you time, consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs you find
- 💡 Suggesting new features
- 📢 Sharing with other Blender users

---

**Happy Blending! 🎨**





