# bl_info = {
#     "name": "Blendpack",
#     "author": "Cloud Blender Render",
#     "version": (1, 0, 0),
#     "blender": (4, 0, 0),
#     "location": "View3D > Sidebar > Blendpack",
#     "description": "Pack all external assets with your blend file for easy sharing",
#     "category": "Import-Export",
# }

# import bpy
# import os
# import shutil
# import zipfile
# import tempfile
# import threading
# import subprocess
# import sys
# import json
# import platform
# import stat
# from pathlib import Path
# from bpy.props import StringProperty, FloatProperty, BoolProperty
# from bpy.types import Operator, Panel, PropertyGroup
# from bpy.app.handlers import persistent

# # ============================================================================
# # PROPERTIES
# # ============================================================================

# class BlendpackProperties(PropertyGroup):
#     output_path: StringProperty(
#         name="Output Path",
#         description="Folder where the packed project will be created",
#         default="",
#         subtype='DIR_PATH'
#     )
#     progress: FloatProperty(
#         name="Progress",
#         default=0.0,
#         min=0.0,
#         max=100.0,
#         subtype='PERCENTAGE'
#     )
#     error_message: StringProperty(
#         name="Error",
#         default=""
#     )
#     show_progress: BoolProperty(
#         name="Show Progress",
#         default=False
#     )
#     is_processing: BoolProperty(
#         name="Is Processing",
#         default=False
#     )
#     status_message: StringProperty(
#         name="Status",
#         default=""
#     )

# @persistent
# def load_handler(dummy):
#     """Reset progress when loading files"""
#     try:
#         props = bpy.context.scene.blendpack_props
#         props.show_progress = False
#         props.progress = 0.0
#         props.error_message = ""
#         props.is_processing = False
#         props.status_message = ""
#     except:
#         pass

# # ============================================================================
# # 7-ZIP BINARY MANAGER
# # ============================================================================

# class SevenZipManager:
#     """Manages 7-Zip binary detection and execution"""
    
#     def __init__(self):
#         self.binary_path = None
#         self.use_7zip = False
#         self.platform_info = self._detect_platform()
#         self._locate_binary()
    
#     def _detect_platform(self):
#         """Detect OS and architecture with comprehensive coverage"""
#         system = platform.system().lower()
#         machine = platform.machine().lower()
        
#         # Normalize OS name
#         if system == "darwin":
#             os_name = "darwin"
#         elif system == "linux":
#             os_name = "linux"
#         elif system == "windows":
#             os_name = "windows"
#         else:
#             os_name = "unknown"
        
#         # Normalize architecture
#         arch = "unknown"
        
#         # 64-bit Intel/AMD
#         if machine in ["x86_64", "amd64", "x64"]:
#             arch = "x64"
        
#         # 32-bit Intel
#         elif machine in ["i386", "i686", "x86"]:
#             arch = "x86"
        
#         # 64-bit ARM
#         elif machine in ["aarch64", "arm64"]:
#             arch = "arm64"
        
#         # 32-bit ARM
#         elif machine in ["armv7l", "armv6l", "arm"]:
#             arch = "arm"
        
#         # PowerPC
#         elif machine in ["ppc64le", "ppc64"]:
#             arch = "ppc64"
        
#         # IBM mainframe
#         elif machine == "s390x":
#             arch = "s390x"
        
#         print(f"[7-Zip] Detected: {os_name} / {arch} (raw: {system} / {machine})")
        
#         return {
#             "os": os_name,
#             "arch": arch,
#             "raw_system": system,
#             "raw_machine": machine
#         }
    
#     def _locate_binary(self):
#         """Locate appropriate 7-Zip binary"""
#         # Get addon directory
#         addon_dir = Path(__file__).parent
#         binaries_dir = addon_dir / "7z_binaries"
        
#         if not binaries_dir.exists():
#             print(f"[7-Zip] Binaries directory not found: {binaries_dir}")
#             self.use_7zip = False
#             return
        
#         os_name = self.platform_info["os"]
#         arch = self.platform_info["arch"]
        
#         # Build binary path based on OS and architecture
#         binary_name = None
#         binary_subpath = None
        
#         if os_name == "windows":
#             binary_name = "7za.exe"
#             if arch in ["x64", "x86"]:
#                 binary_subpath = binaries_dir / "windows" / "x64" / binary_name
#             elif arch == "arm64":
#                 binary_subpath = binaries_dir / "windows" / "arm64" / binary_name
        
#         elif os_name == "linux":
#             binary_name = "7zz"
#             if arch == "x64":
#                 binary_subpath = binaries_dir / "linux" / "x64" / binary_name
#             elif arch == "arm64":
#                 binary_subpath = binaries_dir / "linux" / "arm64" / binary_name
        
#         elif os_name == "darwin":
#             binary_name = "7zz"
#             # macOS binary is universal (works for both Intel and Apple Silicon)
#             binary_subpath = binaries_dir / "darwin" / binary_name
        
#         # Check if binary exists
#         if binary_subpath and binary_subpath.exists():
#             self.binary_path = binary_subpath
            
#             # Make executable on Unix-like systems
#             if os_name in ["linux", "darwin"]:
#                 self._make_executable(binary_subpath)
            
#             self.use_7zip = True
#             print(f"[7-Zip] Binary found: {binary_subpath}")
#         else:
#             print(f"[7-Zip] Binary not found for {os_name}/{arch}")
#             print(f"[7-Zip] Searched: {binary_subpath}")
#             print(f"[7-Zip] Falling back to Python zipfile")
#             self.use_7zip = False
    
#     def _make_executable(self, binary_path):
#         """Add execute permissions for Unix-like systems"""
#         try:
#             current_stat = os.stat(binary_path)
#             os.chmod(binary_path, current_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
#             print(f"[7-Zip] Set executable permissions: {binary_path}")
#         except Exception as e:
#             print(f"[7-Zip] Warning: Could not set executable permissions: {e}")
    
#     def compress(self, source_dir, output_zip, progress_callback=None):
#         """
#         Compress directory using 7-Zip
#         Returns: (success: bool, error_message: str or None)
#         """
#         if not self.use_7zip or not self.binary_path:
#             return False, "7-Zip not available"
        
#         try:
#             # Build 7-Zip command
#             # -tzip = zip format
#             # -mx5 = compression level 5 (balanced speed/size)
#             # -mmt = multi-threaded
#             # -bsp1 = show progress to stdout
#             cmd = [
#                 str(self.binary_path),
#                 "a",                    # Add to archive
#                 "-tzip",                # ZIP format
#                 "-mx5",                 # Compression level (0-9, 5 is balanced)
#                 "-mmt",                 # Multi-threaded
#                 "-bsp1",                # Progress to stdout
#                 str(output_zip),        # Output file
#                 str(source_dir / "*")   # Source (all files in directory)
#             ]
            
#             print(f"[7-Zip] Running: {' '.join(cmd)}")
            
#             # Run 7-Zip process
#             process = subprocess.Popen(
#                 cmd,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 encoding='utf-8',
#                 errors='replace',
#                 bufsize=1,
#                 universal_newlines=True
#             )
            
#             # Parse progress output
#             last_progress = 0.0
#             for line in process.stdout:
#                 line = line.strip()
                
#                 # 7-Zip outputs progress like: "5%" or " 15%"
#                 if "%" in line:
#                     try:
#                         # Extract percentage
#                         percent_str = line.strip().rstrip("%").strip()
#                         if percent_str.isdigit():
#                             current_progress = float(percent_str)
                            
#                             # Update only if changed significantly (reduce overhead)
#                             if current_progress - last_progress >= 1.0:
#                                 if progress_callback:
#                                     # Map 7-Zip progress (0-100) to our range (90-95)
#                                     mapped_progress = 90.0 + (current_progress / 100.0) * 5.0
#                                     progress_callback(mapped_progress, f"Archiving... {int(current_progress)}%")
#                                 last_progress = current_progress
#                     except ValueError:
#                         pass
            
#             # Wait for completion
#             return_code = process.wait(timeout=600)  # 10 minute timeout
            
#             if return_code != 0:
#                 stderr_output = process.stderr.read()
#                 return False, f"7-Zip failed with code {return_code}: {stderr_output}"
            
#             # Verify output exists
#             if not output_zip.exists():
#                 return False, "7-Zip completed but output file not found"
            
#             print(f"[7-Zip] Compression successful: {output_zip}")
#             return True, None
            
#         except subprocess.TimeoutExpired:
#             return False, "7-Zip compression timed out"
#         except Exception as e:
#             return False, f"7-Zip error: {str(e)}"

# # ============================================================================
# # FILE COLLECTOR
# # ============================================================================

# class FileCollector:
#     """Collects all external file references"""
    
#     def __init__(self, blend_path):
#         self.blend_path = Path(blend_path)
#         self.files = {
#             'external': {},      # normalized_path -> (category, metadata)
#             'packed': [],        # packed file info
#             'missing': [],       # missing file paths
#         }
    
#     def collect_all(self):
#         """Collect all assets"""
#         print("\n" + "="*60)
#         print("COLLECTING ALL ASSETS")
#         print("="*60)
        
#         self.collect_images()
#         self.collect_movie_clips()
#         self.collect_sounds()
#         self.collect_fonts()
#         self.collect_texts()
#         self.collect_volumes()
#         self.collect_libraries()
#         self.collect_cache_files()
#         self.collect_shader_nodes()
#         self.collect_compositor_nodes()
#         self.collect_geometry_nodes()
#         self.collect_world_nodes()
        
#         self.print_summary()
#         return self.files
    
#     def add_external_file(self, filepath, category, metadata=None):
#         """Add external file with validation"""
#         if not filepath:
#             return
        
#         abs_path = bpy.path.abspath(filepath)
#         if not abs_path:
#             return
        
#         norm_path = os.path.normpath(abs_path)
        
#         if os.path.exists(norm_path):
#             if norm_path not in self.files['external']:
#                 self.files['external'][norm_path] = (category, metadata or {})
#                 print(f"  ✓ {category}: {Path(norm_path).name}")
#         else:
#             if norm_path not in self.files['missing']:
#                 self.files['missing'].append(norm_path)
#                 print(f"  ✗ MISSING {category}: {norm_path}")
    
#     def add_packed_file(self, file_type, name, data_block, filepath=""):
#         """Add packed file info"""
#         self.files['packed'].append({
#             'type': file_type,
#             'name': name,
#             'data_block': data_block,
#             'original_filepath': filepath
#         })
#         print(f"  📦 Packed {file_type}: {name}")
    
#     def collect_images(self):
#         """Collect all image datablocks"""
#         print("\n[Images]")
#         for img in bpy.data.images:
#             if img.source in ('FILE', 'MOVIE', 'SEQUENCE'):
#                 if img.packed_file:
#                     self.add_packed_file('image', img.name, img, img.filepath)
#                 else:
#                     filepath = bpy.path.abspath(img.filepath, library=img.library)
#                     if not filepath:
#                         continue
                    
#                     category = self.categorize_image(img, filepath)
                    
#                     # Handle image sequences
#                     if img.source == 'SEQUENCE':
#                         sequence_files = self.collect_file_sequence(filepath)
#                         for seq_file in sequence_files:
#                             self.add_external_file(seq_file, 'image_sequences', {
#                                 'is_sequence': True,
#                                 'sequence_base': filepath,
#                                 'data_block_name': img.name
#                             })
#                     else:
#                         self.add_external_file(filepath, category, {
#                             'is_sequence': False,
#                             'source': img.source,
#                             'data_block_name': img.name
#                         })
    
#     def categorize_image(self, img, filepath):
#         """Categorize image files - prioritize extension check"""
#         if not filepath:
#             return 'textures'
        
#         ext = Path(filepath).suffix.lower()
        
#         # Video extensions
#         video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', 
#                      '.wmv', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogg', 
#                      '.ogv', '.qt', '.mxf', '.dv', '.m2v', '.m2ts', '.ts'}
        
#         if ext in video_exts:
#             print(f"    🎥 Video texture: {Path(filepath).name}")
#             return 'videos'
        
#         if hasattr(img, 'source') and img.source == 'MOVIE':
#             return 'videos'
        
#         if img.source == 'SEQUENCE':
#             return 'image_sequences'
        
#         if ext in {'.hdr', '.exr'}:
#             return 'hdris'
        
#         return 'textures'
    
#     def collect_file_sequence(self, filepath):
#         """Collect all files in a sequence"""
#         if not filepath or not os.path.exists(filepath):
#             return [filepath] if filepath else []
        
#         import re
        
#         path_obj = Path(filepath)
#         directory = path_obj.parent
#         filename = path_obj.stem
#         extension = path_obj.suffix
        
#         # Find frame numbers (3+ consecutive digits)
#         matches = list(re.finditer(r'\d{3,}', filename))
        
#         if not matches:
#             return [filepath]
        
#         # Use last match as frame number
#         frame_match = matches[-1]
#         frame_str = frame_match.group()
#         frame_start = frame_match.start()
#         frame_end = frame_match.end()
        
#         prefix = filename[:frame_start]
#         suffix = filename[frame_end:]
#         num_digits = len(frame_str)
        
#         # Find all matching files
#         sequence_files = []
        
#         for potential_file in directory.iterdir():
#             if not potential_file.is_file() or potential_file.suffix != extension:
#                 continue
            
#             pot_stem = potential_file.stem
            
#             if pot_stem.startswith(prefix) and pot_stem.endswith(suffix):
#                 middle = pot_stem[len(prefix):len(pot_stem)-len(suffix)] if suffix else pot_stem[len(prefix):]
                
#                 if middle.isdigit() and len(middle) == num_digits:
#                     sequence_files.append(str(potential_file))
        
#         sequence_files.sort()
        
#         if len(sequence_files) > 1:
#             print(f"    📹 Sequence: {prefix}####.{extension} ({len(sequence_files)} frames)")
#             return sequence_files
        
#         return [filepath]
    
#     def collect_movie_clips(self):
#         """Collect movie clip datablocks"""
#         print("\n[Movie Clips]")
#         for clip in bpy.data.movieclips:
#             filepath = bpy.path.abspath(clip.filepath)
#             self.add_external_file(filepath, 'videos', {'data_block_name': clip.name})
    
#     def collect_sounds(self):
#         """Collect sound datablocks"""
#         print("\n[Sounds]")
#         for sound in bpy.data.sounds:
#             if sound.packed_file:
#                 self.add_packed_file('sound', sound.name, sound, sound.filepath)
#             else:
#                 filepath = bpy.path.abspath(sound.filepath, library=sound.library)
#                 self.add_external_file(filepath, 'sounds', {'data_block_name': sound.name})
    
#     def collect_fonts(self):
#         """Collect font datablocks"""
#         print("\n[Fonts]")
#         for font in bpy.data.fonts:
#             if font.filepath == '<builtin>':
#                 continue
#             if font.packed_file:
#                 self.add_packed_file('font', font.name, font, font.filepath)
#             else:
#                 filepath = bpy.path.abspath(font.filepath, library=font.library)
#                 self.add_external_file(filepath, 'fonts', {'data_block_name': font.name})
    
#     def collect_texts(self):
#         """Collect text datablocks"""
#         print("\n[Text Files]")
#         for text in bpy.data.texts:
#             if not text.is_in_memory and text.filepath:
#                 filepath = bpy.path.abspath(text.filepath)
#                 self.add_external_file(filepath, 'texts', {'data_block_name': text.name})
    
#     def collect_volumes(self):
#         """Collect VDB volume files"""
#         print("\n[Volumes (VDB)]")
#         for obj in bpy.data.objects:
#             if obj.type == 'VOLUME':
#                 if hasattr(obj.data, 'filepath') and obj.data.filepath:
#                     filepath = bpy.path.abspath(obj.data.filepath)
                    
#                     # Check for sequences
#                     if self.is_file_sequence(filepath):
#                         sequence_files = self.collect_file_sequence(filepath)
#                         for seq_file in sequence_files:
#                             self.add_external_file(seq_file, 'vdbs', {
#                                 'is_sequence': True,
#                                 'sequence_base': filepath,
#                                 'data_block_name': obj.name
#                             })
#                     else:
#                         self.add_external_file(filepath, 'vdbs', {
#                             'is_sequence': False,
#                             'data_block_name': obj.name
#                         })
    
#     def is_file_sequence(self, filepath):
#         """Check if filepath contains frame number pattern"""
#         if not filepath or not os.path.exists(filepath):
#             return False
        
#         import re
#         filename = Path(filepath).stem
#         return bool(re.search(r'\d{3,}', filename))
    
#     def collect_libraries(self):
#         """Collect linked library files"""
#         print("\n[Linked Libraries]")
#         for lib in bpy.data.libraries:
#             filepath = bpy.path.abspath(lib.filepath)
#             self.add_external_file(filepath, 'libraries', {'data_block_name': lib.name})
    
#     def collect_cache_files(self):
#         """Collect cache files"""
#         print("\n[Cache Files]")
#         for cache in bpy.data.cache_files:
#             filepath = bpy.path.abspath(cache.filepath)
            
#             ext = Path(filepath).suffix.lower()
#             if ext == '.abc':
#                 category = 'alembic'
#             elif ext in {'.usd', '.usda', '.usdc', '.usdz'}:
#                 category = 'usd'
#             else:
#                 category = 'caches'
            
#             # Check for sequences
#             if self.is_file_sequence(filepath):
#                 sequence_files = self.collect_file_sequence(filepath)
#                 for seq_file in sequence_files:
#                     self.add_external_file(seq_file, category, {
#                         'is_sequence': True,
#                         'sequence_base': filepath,
#                         'data_block_name': cache.name
#                     })
#             else:
#                 self.add_external_file(filepath, category, {
#                     'is_sequence': False,
#                     'data_block_name': cache.name
#                 })
    
#     def collect_shader_nodes(self):
#         """Collect files from shader nodes"""
#         print("\n[Shader Nodes]")
#         for mat in bpy.data.materials:
#             if mat.use_nodes and mat.node_tree:
#                 self._scan_nodes(mat.node_tree.nodes, 'shader')
    
#     def collect_compositor_nodes(self):
#         """Collect files from compositor nodes"""
#         print("\n[Compositor Nodes]")
#         for scene in bpy.data.scenes:
#             if scene.use_nodes and scene.node_tree:
#                 self._scan_nodes(scene.node_tree.nodes, 'compositor')
    
#     def collect_geometry_nodes(self):
#         """Collect files from geometry nodes"""
#         print("\n[Geometry Nodes]")
#         for obj in bpy.data.objects:
#             for mod in obj.modifiers:
#                 if mod.type == 'NODES' and mod.node_group:
#                     self._scan_nodes(mod.node_group.nodes, 'geometry')
    
#     def collect_world_nodes(self):
#         """Collect files from world nodes"""
#         print("\n[World Nodes]")
#         for world in bpy.data.worlds:
#             if world.use_nodes and world.node_tree:
#                 self._scan_nodes(world.node_tree.nodes, 'world')
    
#     def _scan_nodes(self, nodes, context_type):
#         """Scan nodes for file references"""
#         for node in nodes:
#             # Script nodes
#             if hasattr(node, 'filepath') and node.filepath:
#                 filepath = bpy.path.abspath(node.filepath)
#                 self.add_external_file(filepath, 'scripts', {
#                     'node_type': node.type,
#                     'context': context_type
#                 })
            
#             # Image texture nodes (including video textures)
#             if node.type == 'TEX_IMAGE' and hasattr(node, 'image') and node.image:
#                 img = node.image
#                 if img.source in ('FILE', 'MOVIE', 'SEQUENCE') and not img.packed_file:
#                     filepath = bpy.path.abspath(img.filepath, library=img.library)
#                     if filepath:
#                         norm_path = os.path.normpath(filepath)
#                         if norm_path not in self.files['external']:
#                             category = self.categorize_image(img, filepath)
#                             self.add_external_file(filepath, category, {
#                                 'is_sequence': False,
#                                 'source': img.source,
#                                 'data_block_name': img.name,
#                                 'found_in_node': True
#                             })
            
#             # IES texture nodes
#             if node.type == 'TEX_IES' and hasattr(node, 'filepath') and node.filepath:
#                 filepath = bpy.path.abspath(node.filepath)
#                 self.add_external_file(filepath, 'ies', {'node_type': 'IES'})
    
#     def print_summary(self):
#         """Print collection summary"""
#         print("\n" + "="*60)
#         print("COLLECTION SUMMARY")
#         print("="*60)
#         print(f"External files: {len(self.files['external'])}")
#         print(f"Packed files: {len(self.files['packed'])}")
#         print(f"Missing files: {len(self.files['missing'])}")
        
#         if self.files['missing']:
#             print("\n⚠️  MISSING FILES:")
#             for missing in self.files['missing'][:5]:
#                 print(f"  - {missing}")
#             if len(self.files['missing']) > 5:
#                 print(f"  ... and {len(self.files['missing']) - 5} more")
        
#         # Category breakdown
#         categories = {}
#         for filepath, (category, metadata) in self.files['external'].items():
#             categories[category] = categories.get(category, 0) + 1
        
#         print("\nBy category:")
#         for cat, count in sorted(categories.items()):
#             print(f"  {cat}: {count}")
#         print("="*60 + "\n")

# # ============================================================================
# # PACKING TASK
# # ============================================================================

# class PackingTask:
#     """Handles packing process in background thread"""
    
#     def __init__(self, blend_path, output_path, file_data):
#         self.blend_path = Path(blend_path)
#         self.output_path = Path(output_path)
#         self.file_data = file_data
#         self.error = None
#         self.progress = 0.0
#         self.status = ""
#         self.project_path = None
#         self.zip_path = None
#         self.temp_dir = None
#         self.seven_zip = SevenZipManager()
        
#     def execute(self):
#         """Main execution"""
#         try:
#             # Validate
#             if self.file_data['missing']:
#                 missing_name = Path(self.file_data['missing'][0]).name
#                 self.error = f"Critical file missing: {missing_name}"
#                 return False
            
#             # Phase 1: Setup (5%)
#             self.update_progress(5.0, "Setting up project...")
#             self.setup_project_structure()
            
#             # Phase 2: Copy files (35%)
#             self.update_progress(10.0, "Copying assets...")
#             path_mapping = self.copy_external_files()
            
#             # Phase 3: Extract packed (15%)
#             self.update_progress(45.0, "Extracting packed files...")
#             self.extract_packed_files(path_mapping)
            
#             # Phase 4: Create modified blend (25%)
#             self.update_progress(60.0, "Creating portable blend...")
#             success = self.create_modified_blend(path_mapping)
#             if not success:
#                 self.error = "Failed to create modified blend file"
#                 return False
            
#             # Phase 5: Verify (5%)
#             self.update_progress(85.0, "Verifying...")
#             if not self.verify_result():
#                 print("⚠️  Warning: Some paths may not be fully relinked")
            
#             # Phase 6: Archive (10%) - NOW WITH 7-ZIP!
#             self.update_progress(90.0, "Creating archive...")
#             archive_success = self.create_archive_optimized()
#             if not archive_success:
#                 self.error = "Failed to create archive"
#                 return False
            
#             # Phase 7: Cleanup (5%)
#             self.update_progress(95.0, "Cleaning up...")
#             self.cleanup()
            
#             self.update_progress(100.0, "Complete!")
#             return True
            
#         except Exception as e:
#             import traceback
#             self.error = f"{str(e)}\n{traceback.format_exc()}"
#             self.cleanup_on_error()
#             return False
    
#     def update_progress(self, value, message=""):
#         """Update progress"""
#         self.progress = value
#         self.status = message
#         if message:
#             print(f"[{value:5.1f}%] {message}")
    
#     def setup_project_structure(self):
#         """Create folder structure"""
#         blend_name = self.blend_path.stem
#         project_name = f"{blend_name}_blendpack"
        
#         # Handle existing folders
#         has_files = any(self.output_path.iterdir()) if self.output_path.exists() else False
        
#         if has_files:
#             counter = 1
#             while (self.output_path / f"{project_name}_{counter}").exists():
#                 counter += 1
#             self.project_path = self.output_path / f"{project_name}_{counter}"
#         else:
#             self.project_path = self.output_path
        
#         self.project_path.mkdir(parents=True, exist_ok=True)
        
#         # Create assets folder if needed
#         if self.file_data['external'] or self.file_data['packed']:
#             self.assets_path = self.project_path / "assets"
#             self.assets_path.mkdir(exist_ok=True)
            
#             self.category_paths = {
#                 'textures': self.assets_path / "textures",
#                 'videos': self.assets_path / "videos",
#                 'sounds': self.assets_path / "sounds",
#                 'fonts': self.assets_path / "fonts",
#                 'hdris': self.assets_path / "hdris",
#                 'vdbs': self.assets_path / "vdbs",
#                 'image_sequences': self.assets_path / "image_sequences",
#                 'libraries': self.assets_path / "libraries",
#                 'caches': self.assets_path / "caches",
#                 'texts': self.assets_path / "texts",
#                 'alembic': self.assets_path / "alembic",
#                 'usd': self.assets_path / "usd",
#                 'scripts': self.assets_path / "scripts",
#                 'ies': self.assets_path / "ies",
#                 'other': self.assets_path / "other",
#             }
            
#             for folder in self.category_paths.values():
#                 folder.mkdir(exist_ok=True)
#         else:
#             self.category_paths = {}
    
#     def copy_external_files(self):
#         """Copy external files and build path mapping"""
#         path_mapping = {}
#         external_files = self.file_data['external']
        
#         if not external_files:
#             return path_mapping
        
#         total = len(external_files)
        
#         for idx, (old_path, (category, metadata)) in enumerate(external_files.items()):
#             try:
#                 old_path_obj = Path(old_path)
                
#                 target_dir = self.category_paths.get(category, self.category_paths['other'])
                
#                 # Create subdirectory
#                 if len(old_path_obj.parts) > 2:
#                     subdir_parts = old_path_obj.parts[-3:-1]
#                     subdir_name = "_".join(subdir_parts[:2])
#                     subdir_name = "".join(c for c in subdir_name if c.isalnum() or c in "._- ")
#                     target_dir = target_dir / subdir_name
#                     target_dir.mkdir(parents=True, exist_ok=True)
                
#                 # Handle name conflicts
#                 new_path = target_dir / old_path_obj.name
#                 counter = 1
#                 while new_path.exists():
#                     stem = old_path_obj.stem
#                     suffix = old_path_obj.suffix
#                     new_path = target_dir / f"{stem}_{counter}{suffix}"
#                     counter += 1
                
#                 # Copy
#                 shutil.copy2(old_path, new_path)
#                 path_mapping[old_path] = str(new_path)
                
#                 # Update progress
#                 if idx % max(1, total // 10) == 0:
#                     progress = 10.0 + (idx + 1) / total * 35.0
#                     msg = f"Copying... ({idx+1}/{total})"
#                     self.update_progress(progress, msg)
                
#             except Exception as e:
#                 print(f"  ⚠️  Error copying {old_path_obj.name}: {e}")
        
#         return path_mapping
    
#     def extract_packed_files(self, path_mapping):
#         """Extract packed files"""
#         if not self.file_data['packed']:
#             return
        
#         self.temp_dir = tempfile.mkdtemp(prefix="blendpack_")
#         total = len(self.file_data['packed'])
        
#         for idx, packed_info in enumerate(self.file_data['packed']):
#             try:
#                 file_type = packed_info['type']
#                 name = packed_info['name']
#                 data_block = packed_info['data_block']
                
#                 # Determine category
#                 if file_type == 'image':
#                     ext = Path(name).suffix or '.png'
#                     category = 'hdris' if ext.lower() in {'.hdr', '.exr'} else 'textures'
#                 elif file_type == 'sound':
#                     category = 'sounds'
#                     ext = Path(name).suffix or '.wav'
#                 elif file_type == 'font':
#                     category = 'fonts'
#                     ext = Path(name).suffix or '.ttf'
#                 else:
#                     category = 'other'
#                     ext = '.dat'
                
#                 target_dir = self.category_paths.get(category, self.category_paths['other'])
                
#                 # Create filename
#                 safe_name = "".join(c for c in Path(name).stem if c.isalnum() or c in "._- ")
#                 if not safe_name:
#                     safe_name = f"packed_{file_type}"
                
#                 new_path = target_dir / f"{safe_name}{ext}"
#                 counter = 1
#                 while new_path.exists():
#                     new_path = target_dir / f"{safe_name}_{counter}{ext}"
#                     counter += 1
                
#                 # Extract
#                 if hasattr(data_block, 'packed_file') and data_block.packed_file:
#                     if file_type == 'image':
#                         temp_file = Path(self.temp_dir) / f"temp_{idx}{ext}"
#                         data_block.filepath_raw = str(temp_file)
#                         data_block.save()
#                         if temp_file.exists():
#                             shutil.move(str(temp_file), str(new_path))
#                     else:
#                         packed_data = data_block.packed_file.data
#                         new_path.write_bytes(bytes(packed_data))
                    
#                     # Map
#                     if packed_info['original_filepath']:
#                         original_abs = str(self.blend_path.parent / packed_info['original_filepath'].replace('//', ''))
#                         path_mapping[os.path.normpath(original_abs)] = str(new_path)
                    
#                     print(f"  ✓ Extracted: {name}")
                
#                 if idx % max(1, total // 5) == 0:
#                     progress = 45.0 + (idx + 1) / total * 15.0
#                     msg = f"Extracting... ({idx+1}/{total})"
#                     self.update_progress(progress, msg)
                
#             except Exception as e:
#                 print(f"  ⚠️  Error extracting: {e}")
    
#     def create_modified_blend(self, path_mapping):
#         """Create modified blend using robust relinking"""
#         # Copy blend
#         dest_blend = self.project_path / f"{self.blend_path.stem}_clone.blend"
#         shutil.copy2(self.blend_path, dest_blend)
        
#         # Build a RELATIVE path mapping
#         relative_mapping = {}
        
#         print("\n" + "="*60)
#         print("BUILDING PATH MAPPING FOR CLONE")
#         print("="*60)
#         print(f"Original blend: {self.blend_path}")
#         print(f"Clone blend: {dest_blend}")
        
#         for old_abs_path, new_abs_path in path_mapping.items():
#             # Calculate what the relative path WAS in the original
#             try:
#                 old_rel_from_original = os.path.relpath(old_abs_path, self.blend_path.parent)
#                 old_rel_blender = "//" + old_rel_from_original.replace("\\", "/")
#             except:
#                 old_rel_blender = old_abs_path
            
#             # Calculate what the relative path SHOULD BE in the clone
#             try:
#                 new_rel_from_clone = os.path.relpath(new_abs_path, dest_blend.parent)
#                 new_rel_blender = "//" + new_rel_from_clone.replace("\\", "/")
#             except:
#                 new_rel_blender = new_abs_path
            
#             # Store BOTH mappings
#             relative_mapping[os.path.normpath(old_abs_path)] = new_rel_blender
#             relative_mapping[old_rel_blender] = new_rel_blender
            
#             print(f"  {old_rel_blender}")
#             print(f"    -> {new_rel_blender}")
        
#         print("="*60 + "\n")
        
#         # Save mapping to JSON
#         mapping_file = self.project_path / "path_mapping.json"
#         with open(mapping_file, 'w', encoding='utf-8') as f:
#             json.dump({
#                 'project_path': str(self.project_path),
#                 'clone_blend_path': str(dest_blend),
#                 'mapping': relative_mapping
#             }, f, indent=2)
        
#         # Generate script
#         script = self.generate_relink_script(mapping_file)
#         script_path = self.project_path / "relink_script.py"
#         script_path.write_text(script, encoding='utf-8')
        
#         # Run Blender subprocess
#         blender_exe = bpy.app.binary_path
#         cmd = [
#             str(blender_exe),
#             str(dest_blend),
#             '--background',
#             '--python', str(script_path)
#         ]
        
#         print(f"\nRunning: {' '.join(cmd)}\n")
        
#         try:
#             result = subprocess.run(
#                 cmd,
#                 capture_output=True,
#                 text=True,
#                 timeout=300,
#                 encoding='utf-8',
#                 errors='replace'
#             )
            
#             # Cleanup
#             script_path.unlink()
#             mapping_file.unlink()
            
#             if result.returncode != 0:
#                 print(f"Subprocess error:\n{result.stderr}")
#                 print(f"Subprocess output:\n{result.stdout}")
#                 return False
            
#             print("✓ Relinking completed!")
#             return True
            
#         except subprocess.TimeoutExpired:
#             self.error = "Relinking timed out"
#             return False
#         except Exception as e:
#             self.error = f"Subprocess failed: {e}"
#             return False
    
#     def generate_relink_script(self, mapping_file):
#         """Generate comprehensive relinking script"""
#         script = f'''import bpy
# import os
# import json
# from pathlib import Path

# # Load mapping
# with open(r"{str(mapping_file)}", 'r', encoding='utf-8') as f:
#     data = json.load(f)

# project_path = Path(data['project_path'])
# clone_blend_path = Path(data['clone_blend_path'])
# path_mapping = data['mapping']

# print("="*60)
# print("RELINKING ALL ASSETS")
# print("="*60)
# print(f"Project: {{project_path}}")
# print(f"Clone: {{clone_blend_path}}")
# print(f"Mappings: {{len(path_mapping)}}")

# def normalize_path(path):
#     """Normalize path for comparison"""
#     if not path:
#         return ""
#     try:
#         # Handle both absolute and relative paths
#         if path.startswith("//"):
#             # Relative path - resolve from blend file location
#             rel_part = path[2:].replace("/", os.sep)
#             abs_path = os.path.join(os.path.dirname(bpy.data.filepath), rel_part)
#             return os.path.normpath(abs_path)
#         else:
#             # Absolute path
#             abs_path = bpy.path.abspath(path)
#             return os.path.normpath(abs_path)
#     except:
#         return os.path.normpath(path)

# def relink_path(old_path):
#     """Relink a path using multiple matching strategies"""
#     if not old_path:
#         return None
    
#     # Strategy 1: Try the path as-is
#     if old_path in path_mapping:
#         return path_mapping[old_path]
    
#     # Strategy 2: Try normalized absolute path
#     norm_abs = normalize_path(old_path)
#     if norm_abs in path_mapping:
#         return path_mapping[norm_abs]
    
#     # Strategy 3: Try with forward slashes
#     old_path_forward = old_path.replace("\\\\", "/")
#     if old_path_forward in path_mapping:
#         return path_mapping[old_path_forward]
    
#     return None

# stats = {{
#     'images': 0,
#     'clips': 0,
#     'sounds': 0,
#     'fonts': 0,
#     'texts': 0,
#     'volumes': 0,
#     'libraries': 0,
#     'caches': 0
# }}

# # Relink Images
# print("\\n[Images]")
# for img in bpy.data.images:
#     if img.source in ('FILE', 'MOVIE', 'SEQUENCE') and not img.packed_file:
#         old_path = img.filepath
#         new_path = relink_path(old_path)
#         if new_path:
#             img.filepath = new_path
#             stats['images'] += 1
#             print(f"  ✓ {{img.name}}: {{old_path}} -> {{new_path}}")
#         else:
#             print(f"  ✗ {{img.name}}: No mapping for {{old_path}}")

# # Relink Movie Clips
# print("\\n[Movie Clips]")
# for clip in bpy.data.movieclips:
#     old_path = clip.filepath
#     new_path = relink_path(old_path)
#     if new_path:
#         clip.filepath = new_path
#         stats['clips'] += 1
#         print(f"  ✓ {{clip.name}}: {{old_path}} -> {{new_path}}")

# # Relink Sounds
# print("\\n[Sounds]")
# for sound in bpy.data.sounds:
#     if not sound.packed_file:
#         old_path = sound.filepath
#         new_path = relink_path(old_path)
#         if new_path:
#             sound.filepath = new_path
#             stats['sounds'] += 1
#             print(f"  ✓ {{sound.name}}")

# # Relink Fonts
# print("\\n[Fonts]")
# for font in bpy.data.fonts:
#     if not font.packed_file and font.filepath != '<builtin>':
#         old_path = font.filepath
#         new_path = relink_path(old_path)
#         if new_path:
#             font.filepath = new_path
#             stats['fonts'] += 1
#             print(f"  ✓ {{font.name}}")

# # Relink Text Files
# print("\\n[Text Files]")
# for text in bpy.data.texts:
#     if not text.is_in_memory and text.filepath:
#         old_path = text.filepath
#         new_path = relink_path(old_path)
#         if new_path:
#             text.filepath = new_path
#             stats['texts'] += 1
#             print(f"  ✓ {{text.name}}")

# # Relink Volumes
# print("\\n[Volumes]")
# for obj in bpy.data.objects:
#     if obj.type == 'VOLUME':
#         if hasattr(obj.data, 'filepath') and obj.data.filepath:
#             old_path = obj.data.filepath
#             new_path = relink_path(old_path)
#             if new_path:
#                 obj.data.filepath = new_path
#                 stats['volumes'] += 1
#                 print(f"  ✓ {{obj.name}}: {{old_path}} -> {{new_path}}")
#             else:
#                 print(f"  ✗ {{obj.name}}: No mapping for {{old_path}}")

# # Relink Libraries
# print("\\n[Libraries]")
# for lib in bpy.data.libraries:
#     old_path = lib.filepath
#     new_path = relink_path(old_path)
#     if new_path:
#         lib.filepath = new_path
#         stats['libraries'] += 1
#         print(f"  ✓ {{lib.name}}")

# # Relink Cache Files
# print("\\n[Cache Files]")
# for cache in bpy.data.cache_files:
#     old_path = cache.filepath
#     new_path = relink_path(old_path)
#     if new_path:
#         cache.filepath = new_path
#         stats['caches'] += 1
#         print(f"  ✓ {{cache.name}}")

# # Save
# print("\\n[Saving]")
# bpy.ops.wm.save_mainfile()
# print("✓ Saved!")

# print("\\n" + "="*60)
# print("RELINKING SUMMARY")
# print("="*60)
# for key, value in stats.items():
#     if value > 0:
#         print(f"  {{key}}: {{value}}")
# print("="*60)
# '''
#         return script
    
#     def verify_result(self):
#         """Verify packed project"""
#         print("\n" + "="*60)
#         print("VERIFYING")
#         print("="*60)
        
#         clone_blend = self.project_path / f"{self.blend_path.stem}_clone.blend"
#         if not clone_blend.exists():
#             print("✗ Clone not found")
#             return False
        
#         print("✓ Clone exists")
        
#         if self.file_data['external'] or self.file_data['packed']:
#             if not self.assets_path.exists():
#                 print("✗ Assets folder missing")
#                 return False
#             print("✓ Assets folder exists")
        
#         total = 0
#         for category, path in self.category_paths.items():
#             if path.exists():
#                 count = sum(1 for f in path.rglob('*') if f.is_file())
#                 if count > 0:
#                     print(f"  {category}: {count}")
#                     total += count
        
#         print(f"✓ Total assets: {total}")
#         print("="*60)
#         return True
    
#     def create_archive_optimized(self):
#         """Create archive using 7-Zip with fallback to zipfile"""
#         project_name = self.project_path.name if self.project_path != self.output_path else f"{self.blend_path.stem}_blendpack"
#         self.zip_path = self.output_path / f"{project_name}.zip"
        
#         print("\n" + "="*60)
#         print("CREATING ARCHIVE")
#         print("="*60)
#         print(f"Method: {'7-Zip' if self.seven_zip.use_7zip else 'Python zipfile'}")
#         print(f"Output: {self.zip_path}")
#         print("="*60 + "\n")
        
#         # Try 7-Zip first
#         if self.seven_zip.use_7zip:
#             success, error = self.seven_zip.compress(
#                 self.project_path,
#                 self.zip_path,
#                 progress_callback=self.update_progress
#             )
            
#             if success:
#                 final_size = self.zip_path.stat().st_size
#                 print(f"\n✓ 7-Zip compression successful!")
#                 print(f"  Archive size: {final_size / (1024*1024):.2f} MB")
#                 return True
#             else:
#                 print(f"\n⚠️  7-Zip failed: {error}")
#                 print("Falling back to Python zipfile...")
        
#         # Fallback to Python zipfile
#         return self.create_archive_fallback()
    
#     def create_archive_fallback(self):
#         """Fallback archive creation using Python zipfile"""
#         project_name = self.project_path.name if self.project_path != self.output_path else f"{self.blend_path.stem}_blendpack"
#         self.zip_path = self.output_path / f"{project_name}.zip"
#         temp_zip = self.output_path / f"{project_name}_temp.zip"
        
#         try:
#             # Collect all files first
#             print("\n[Collecting files for archive...]")
#             files = []
#             total_size = 0
            
#             for root, dirs, filenames in os.walk(self.project_path):
#                 for filename in filenames:
#                     file_path = Path(root) / filename
#                     # Don't include the zip file itself
#                     if file_path.absolute() != self.zip_path.absolute() and file_path.absolute() != temp_zip.absolute():
#                         try:
#                             file_size = file_path.stat().st_size
#                             files.append((file_path, file_size))
#                             total_size += file_size
#                         except OSError as e:
#                             print(f"  ⚠️  Warning: Could not stat {file_path.name}: {e}")
            
#             total_files = len(files)
#             print(f"  Files to archive: {total_files}")
#             print(f"  Total size: {total_size / (1024*1024):.2f} MB")
            
#             # Create zip with progress tracking
#             processed_size = 0
#             last_progress = 90.0
            
#             with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as zipf:
#                 for idx, (file_path, file_size) in enumerate(files):
#                     try:
#                         arcname = file_path.relative_to(self.project_path)
#                         zipf.write(file_path, arcname)
                        
#                         processed_size += file_size
                        
#                         # Update progress based on size processed
#                         if total_size > 0:
#                             size_progress = (processed_size / total_size) * 5.0  # 5% of total progress
#                             current_progress = 90.0 + size_progress
                            
#                             # Only update if progress changed significantly
#                             if current_progress - last_progress >= 0.5:
#                                 msg = f"Archiving... ({idx+1}/{total_files})"
#                                 self.update_progress(current_progress, msg)
#                                 last_progress = current_progress
                        
#                     except Exception as e:
#                         print(f"  ⚠️  Warning: Could not add {file_path.name} to archive: {e}")
            
#             # Replace old zip with new one atomically
#             if self.zip_path.exists():
#                 self.zip_path.unlink()
#             temp_zip.rename(self.zip_path)
            
#             final_size = self.zip_path.stat().st_size
#             print(f"\n✓ Archive created: {self.zip_path}")
#             print(f"  Compressed size: {final_size / (1024*1024):.2f} MB")
#             print(f"  Compression ratio: {(1 - final_size/total_size)*100:.1f}%" if total_size > 0 else "")
            
#             return True
            
#         except Exception as e:
#             print(f"\n✗ Archive creation failed: {e}")
#             if temp_zip.exists():
#                 try:
#                     temp_zip.unlink()
#                 except:
#                     pass
#             return False
    
#     def cleanup(self):
#         """Cleanup temp files"""
#         try:
#             if self.temp_dir and os.path.exists(self.temp_dir):
#                 shutil.rmtree(self.temp_dir)
            
#             if self.project_path and self.project_path != self.output_path:
#                 if self.project_path.exists():
#                     shutil.rmtree(self.project_path)
#                     print("✓ Cleaned up")
#         except Exception as e:
#             print(f"⚠️  Cleanup warning: {e}")
    
#     def cleanup_on_error(self):
#         """Cleanup on error"""
#         try:
#             if self.temp_dir and os.path.exists(self.temp_dir):
#                 shutil.rmtree(self.temp_dir)
#             if self.project_path and self.project_path.exists():
#                 if self.project_path != self.output_path:
#                     shutil.rmtree(self.project_path)
#             if self.zip_path and self.zip_path.exists():
#                 self.zip_path.unlink()
#         except:
#             pass

# # ============================================================================
# # OPERATORS
# # ============================================================================

# class BLENDPACK_OT_select_folder(Operator):
#     bl_idname = "blendpack.select_folder"
#     bl_label = "Select Folder"
#     bl_description = "Select output folder"
#     bl_options = {'INTERNAL'}
    
#     directory: StringProperty(subtype='DIR_PATH')
    
#     def invoke(self, context, event):
#         context.window_manager.fileselect_add(self)
#         return {'RUNNING_MODAL'}
    
#     def execute(self, context):
#         context.scene.blendpack_props.output_path = self.directory
#         context.scene.blendpack_props.error_message = ""
#         return {'FINISHED'}


# class BLENDPACK_OT_start_packing(Operator):
#     bl_idname = "blendpack.start_packing"
#     bl_label = "Start Packing"
#     bl_description = "Pack all assets"
    
#     _timer = None
#     _thread = None
#     _task = None
#     _hide_timer = None
    
#     def modal(self, context, event):
#         """Modal handler"""
#         if event.type == 'TIMER':
#             props = context.scene.blendpack_props
            
#             # Hide progress bar
#             if self._hide_timer:
#                 props.show_progress = False
#                 props.progress = 0.0
#                 props.status_message = ""
#                 context.window_manager.event_timer_remove(self._hide_timer)
#                 self._hide_timer = None
#                 return {'FINISHED'}
            
#             # Update from task
#             if self._task and self._thread:
#                 props.progress = self._task.progress
#                 props.status_message = self._task.status
                
#                 # Check if done
#                 if not self._thread.is_alive():
#                     wm = context.window_manager
#                     wm.event_timer_remove(self._timer)
#                     self._timer = None
                    
#                     if self._task.error:
#                         props.error_message = self._task.error
#                         props.is_processing = False
#                         props.show_progress = False
#                         props.status_message = ""
#                         self.report({'ERROR'}, f"Failed: {self._task.error}")
#                         return {'CANCELLED'}
#                     else:
#                         props.is_processing = False
#                         self.report({'INFO'}, f"Packed: {self._task.zip_path}")
                        
#                         # Hide after 3s
#                         self._hide_timer = wm.event_timer_add(3.0, window=context.window)
#                         return {'RUNNING_MODAL'}
            
#             # Redraw
#             for window in context.window_manager.windows:
#                 for area in window.screen.areas:
#                     if area.type == 'VIEW_3D':
#                         area.tag_redraw()
        
#         return {'PASS_THROUGH'}
    
#     def execute(self, context):
#         props = context.scene.blendpack_props
        
#         # Validate
#         if props.is_processing:
#             self.report({'WARNING'}, "Already processing")
#             return {'CANCELLED'}
        
#         if not props.output_path or not os.path.isdir(props.output_path):
#             props.error_message = "Select valid output folder"
#             return {'CANCELLED'}
        
#         blend_path = bpy.data.filepath
#         if not blend_path:
#             props.error_message = "Save blend file first"
#             return {'CANCELLED'}
        
#         # Reset
#         props.error_message = ""
#         props.progress = 0.0
#         props.status_message = ""
#         props.show_progress = True
#         props.is_processing = True
        
#         # Collect files
#         print("\n" + "="*60)
#         print("BLENDPACK v2.1 - STARTING")
#         print("="*60)
#         print(f"Blend: {blend_path}")
#         print(f"Output: {props.output_path}")
        
#         try:
#             collector = FileCollector(blend_path)
#             file_data = collector.collect_all()
#         except Exception as e:
#             props.error_message = f"Collection failed: {str(e)}"
#             props.is_processing = False
#             props.show_progress = False
#             return {'CANCELLED'}
        
#         # Create task
#         self._task = PackingTask(blend_path, props.output_path, file_data)
        
#         # Start thread
#         self._thread = threading.Thread(target=self._task.execute, daemon=True)
#         self._thread.start()
        
#         # Start modal
#         wm = context.window_manager
#         self._timer = wm.event_timer_add(0.1, window=context.window)
#         wm.modal_handler_add(self)
        
#         return {'RUNNING_MODAL'}
    
#     def cancel(self, context):
#         """Cancel handler"""
#         if self._timer:
#             context.window_manager.event_timer_remove(self._timer)
#         if self._hide_timer:
#             context.window_manager.event_timer_remove(self._hide_timer)

# # ============================================================================
# # UI
# # ============================================================================

# class BLENDPACK_PT_main_panel(Panel):
#     bl_label = "Blendpack"
#     bl_idname = "BLENDPACK_PT_main_panel"
#     bl_space_type = 'VIEW_3D'
#     bl_region_type = 'UI'
#     bl_category = 'Blendpack'
#     bl_options = {'DEFAULT_CLOSED'}
    
#     def draw(self, context):
#         layout = self.layout
#         layout.use_property_split = False
#         layout.use_property_decorate = False
#         layout.scale_x = 1.5
        
#         props = context.scene.blendpack_props
        
#         # Header
#         box = layout.box()
#         col = box.column(align=True)
#         col.label(text="Blendpack", icon='PACKAGE')
#         col.separator(factor=0.5)
        
#         # Description
#         desc = box.column(align=True)
#         desc.scale_y = 0.8
#         desc.label(text="Pack all external assets with your")
#         desc.label(text="blend file for easy sharing without")
#         desc.label(text="missing files.")
        
#         box.separator(factor=0.5)
        
#         # Credits
#         credit = box.column(align=True)
#         credit.scale_y = 0.7
#         credit.label(text="Created by Cloud Blender Render")
#         credit.label(text="Get RTX 5090 for $0.69/hour")
        
#         # Link
#         row = box.row()
#         row.scale_y = 0.8
#         row.operator("wm.url_open", text="Learn More", icon='URL').url = "https://cloud-blender-render.rahulahire.com/"
        
#         layout.separator()
        
#         # Output selector
#         box = layout.box()
#         col = box.column(align=True)
#         col.label(text="Output Folder:")
        
#         sub = col.column(align=True)
#         sub.enabled = False
#         if props.output_path:
#             sub.label(text=props.output_path, icon='FOLDER_REDIRECT')
#         else:
#             sub.label(text="No folder selected", icon='FOLDER_REDIRECT')
        
#         col.operator("blendpack.select_folder", text="Select Folder", icon='FILEBROWSER')
        
#         layout.separator()
        
#         # Start button
#         row = layout.row()
#         row.scale_y = 1.5
#         row.enabled = not props.is_processing
#         if props.is_processing:
#             row.operator("blendpack.start_packing", text="Processing...", icon='TIME')
#         else:
#             row.operator("blendpack.start_packing", text="Start Packing", icon='EXPORT')
        
#         # Progress
#         if props.show_progress:
#             box = layout.box()
#             col = box.column(align=True)
#             col.prop(props, "progress", text="Progress", slider=True)
#             if props.status_message:
#                 col.label(text=props.status_message, icon='INFO')
        
#         # Error
#         if props.error_message:
#             box = layout.box()
#             col = box.column(align=True)
#             col.alert = True
#             col.scale_y = 0.7
#             col.label(text="Error:", icon='ERROR')
#             lines = props.error_message.split('\n')
#             for line in lines[:5]:
#                 words = line.split()
#                 text_line = ""
#                 for word in words:
#                     if len(text_line + word) > 40:
#                         col.label(text=text_line)
#                         text_line = word + " "
#                     else:
#                         text_line += word + " "
#                 if text_line:
#                     col.label(text=text_line.strip())

# # ============================================================================
# # REGISTRATION
# # ============================================================================

# classes = (
#     BlendpackProperties,
#     BLENDPACK_OT_select_folder,
#     BLENDPACK_OT_start_packing,
#     BLENDPACK_PT_main_panel,
# )

# def register():
#     for cls in classes:
#         bpy.utils.register_class(cls)
#     bpy.types.Scene.blendpack_props = bpy.props.PointerProperty(type=BlendpackProperties)
    
#     if load_handler not in bpy.app.handlers.load_post:
#         bpy.app.handlers.load_post.append(load_handler)
    
#     print("Blendpack v2.1 registered")

# def unregister():
#     if load_handler in bpy.app.handlers.load_post:
#         bpy.app.handlers.load_post.remove(load_handler)
    
#     for cls in reversed(classes):
#         bpy.utils.unregister_class(cls)
    
#     if hasattr(bpy.types.Scene, 'blendpack_props'):
#         del bpy.types.Scene.blendpack_props
    
#     print("Blendpack v2.1 unregistered")

# if __name__ == "__main__":
#     register()


bl_info = {
    "name": "Blendpack",
    "author": "Cloud Blender Render",
    "version": (2, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Blendpack",
    "description": "Pack all external assets with your blend file for easy sharing",
    "category": "Import-Export",
}

import bpy
import os
import shutil
import zipfile
import tempfile
import threading
import subprocess
import sys
import json
import platform
import stat
from pathlib import Path
from bpy.props import StringProperty, FloatProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy.app.handlers import persistent

# ============================================================================
# PROPERTIES
# ============================================================================

class BlendpackProperties(PropertyGroup):
    output_path: StringProperty(
        name="Output Path",
        description="Folder where the packed project will be created",
        default="",
        subtype='DIR_PATH'
    )
    progress: FloatProperty(
        name="Progress",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype='PERCENTAGE'
    )
    error_message: StringProperty(
        name="Error",
        default=""
    )
    show_progress: BoolProperty(
        name="Show Progress",
        default=False
    )
    is_processing: BoolProperty(
        name="Is Processing",
        default=False
    )
    status_message: StringProperty(
        name="Status",
        default=""
    )

@persistent
def load_handler(dummy):
    """Reset progress when loading files"""
    try:
        props = bpy.context.scene.blendpack_props
        props.show_progress = False
        props.progress = 0.0
        props.error_message = ""
        props.is_processing = False
        props.status_message = ""
    except:
        pass

# ============================================================================
# 7-ZIP BINARY MANAGER
# ============================================================================

class SevenZipManager:
    """Manages 7-Zip binary detection and execution"""
    
    def __init__(self):
        self.binary_path = None
        self.use_7zip = False
        self.platform_info = self._detect_platform()
        self._locate_binary()
    
    def _detect_platform(self):
        """Detect OS and architecture with comprehensive coverage"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Normalize OS name
        if system == "darwin":
            os_name = "darwin"
        elif system == "linux":
            os_name = "linux"
        elif system == "windows":
            os_name = "windows"
        else:
            os_name = "unknown"
        
        # Normalize architecture
        arch = "unknown"
        
        # 64-bit Intel/AMD
        if machine in ["x86_64", "amd64", "x64"]:
            arch = "x64"
        
        # 32-bit Intel
        elif machine in ["i386", "i686", "x86"]:
            arch = "x86"
        
        # 64-bit ARM
        elif machine in ["aarch64", "arm64"]:
            arch = "arm64"
        
        # 32-bit ARM
        elif machine in ["armv7l", "armv6l", "arm"]:
            arch = "arm"
        
        # PowerPC
        elif machine in ["ppc64le", "ppc64"]:
            arch = "ppc64"
        
        # IBM mainframe
        elif machine == "s390x":
            arch = "s390x"
        
        print(f"[7-Zip] Detected: {os_name} / {arch} (raw: {system} / {machine})")
        
        return {
            "os": os_name,
            "arch": arch,
            "raw_system": system,
            "raw_machine": machine
        }
    
    def _locate_binary(self):
        """Locate appropriate 7-Zip binary"""
        # Get addon directory
        addon_dir = Path(__file__).parent
        binaries_dir = addon_dir / "7z_binaries"
        
        if not binaries_dir.exists():
            print(f"[7-Zip] Binaries directory not found: {binaries_dir}")
            self.use_7zip = False
            return
        
        os_name = self.platform_info["os"]
        arch = self.platform_info["arch"]
        
        # Build binary path based on OS and architecture
        binary_name = None
        binary_subpath = None
        
        if os_name == "windows":
            binary_name = "7za.exe"
            if arch in ["x64", "x86"]:
                binary_subpath = binaries_dir / "windows" / "x64" / binary_name
            elif arch == "arm64":
                binary_subpath = binaries_dir / "windows" / "arm64" / binary_name
        
        elif os_name == "linux":
            binary_name = "7zz"
            if arch == "x64":
                binary_subpath = binaries_dir / "linux" / "x64" / binary_name
            elif arch == "arm64":
                binary_subpath = binaries_dir / "linux" / "arm64" / binary_name
        
        elif os_name == "darwin":
            binary_name = "7zz"
            # macOS binary is universal (works for both Intel and Apple Silicon)
            binary_subpath = binaries_dir / "darwin" / binary_name
        
        # Check if binary exists
        if binary_subpath and binary_subpath.exists():
            self.binary_path = binary_subpath
            
            # Make executable on Unix-like systems
            if os_name in ["linux", "darwin"]:
                self._make_executable(binary_subpath)
            
            self.use_7zip = True
            print(f"[7-Zip] Binary found: {binary_subpath}")
        else:
            print(f"[7-Zip] Binary not found for {os_name}/{arch}")
            print(f"[7-Zip] Searched: {binary_subpath}")
            print(f"[7-Zip] Falling back to Python zipfile")
            self.use_7zip = False
    
    def _make_executable(self, binary_path):
        """Add execute permissions for Unix-like systems"""
        try:
            current_stat = os.stat(binary_path)
            os.chmod(binary_path, current_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"[7-Zip] Set executable permissions: {binary_path}")
        except Exception as e:
            print(f"[7-Zip] Warning: Could not set executable permissions: {e}")
    
    def compress(self, source_dir, output_zip, progress_callback=None):
        """
        Compress directory using 7-Zip
        Returns: (success: bool, error_message: str or None)
        """
        if not self.use_7zip or not self.binary_path:
            return False, "7-Zip not available"
        
        try:
            # Build 7-Zip command
            # -tzip = zip format
            # -mx5 = compression level 5 (balanced speed/size)
            # -mmt = multi-threaded
            # -bsp1 = show progress to stdout
            cmd = [
                str(self.binary_path),
                "a",                    # Add to archive
                "-tzip",                # ZIP format
                "-mx5",                 # Compression level (0-9, 5 is balanced)
                "-mmt",                 # Multi-threaded
                "-bsp1",                # Progress to stdout
                str(output_zip),        # Output file
                str(source_dir / "*")   # Source (all files in directory)
            ]
            
            print(f"[7-Zip] Running: {' '.join(cmd)}")
            
            # Run 7-Zip process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                universal_newlines=True
            )
            
            # Parse progress output
            last_progress = 0.0
            for line in process.stdout:
                line = line.strip()
                
                # 7-Zip outputs progress like: "5%" or " 15%"
                if "%" in line:
                    try:
                        # Extract percentage
                        percent_str = line.strip().rstrip("%").strip()
                        if percent_str.isdigit():
                            current_progress = float(percent_str)
                            
                            # Update only if changed significantly (reduce overhead)
                            if current_progress - last_progress >= 1.0:
                                if progress_callback:
                                    # Map 7-Zip progress (0-100) to our range (90-95)
                                    mapped_progress = 90.0 + (current_progress / 100.0) * 5.0
                                    progress_callback(mapped_progress, f"Archiving... {int(current_progress)}%")
                                last_progress = current_progress
                    except ValueError:
                        pass
            
            # Wait for completion
            return_code = process.wait(timeout=600)  # 10 minute timeout
            
            # CRITICAL: Update progress immediately after 7-Zip completes
            if progress_callback:
                progress_callback(95.0, "Archive complete!")
            
            if return_code != 0:
                stderr_output = process.stderr.read()
                return False, f"7-Zip failed with code {return_code}: {stderr_output}"
            
            # Verify output exists
            if not output_zip.exists():
                return False, "7-Zip completed but output file not found"
            
            print(f"[7-Zip] Compression successful: {output_zip}")
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "7-Zip compression timed out"
        except Exception as e:
            return False, f"7-Zip error: {str(e)}"

# ============================================================================
# FILE COLLECTOR
# ============================================================================

class FileCollector:
    """Collects all external file references"""
    
    def __init__(self, blend_path):
        self.blend_path = Path(blend_path)
        self.files = {
            'external': {},      # normalized_path -> (category, metadata)
            'packed': [],        # packed file info
            'missing': [],       # missing file paths
        }
    
    def collect_all(self):
        """Collect all assets"""
        print("\n" + "="*60)
        print("COLLECTING ALL ASSETS")
        print("="*60)
        
        self.collect_images()
        self.collect_movie_clips()
        self.collect_sounds()
        self.collect_fonts()
        self.collect_texts()
        self.collect_volumes()
        self.collect_libraries()
        self.collect_cache_files()
        self.collect_shader_nodes()
        self.collect_compositor_nodes()
        self.collect_geometry_nodes()
        self.collect_world_nodes()
        
        self.print_summary()
        return self.files
    
    def add_external_file(self, filepath, category, metadata=None):
        """Add external file with validation"""
        if not filepath:
            return
        
        abs_path = bpy.path.abspath(filepath)
        if not abs_path:
            return
        
        norm_path = os.path.normpath(abs_path)
        
        if os.path.exists(norm_path):
            if norm_path not in self.files['external']:
                self.files['external'][norm_path] = (category, metadata or {})
                print(f"  ✓ {category}: {Path(norm_path).name}")
        else:
            if norm_path not in self.files['missing']:
                self.files['missing'].append(norm_path)
                print(f"  ✗ MISSING {category}: {norm_path}")
    
    def add_packed_file(self, file_type, name, data_block, filepath=""):
        """Add packed file info"""
        self.files['packed'].append({
            'type': file_type,
            'name': name,
            'data_block': data_block,
            'original_filepath': filepath
        })
        print(f"  📦 Packed {file_type}: {name}")
    
    def collect_images(self):
        """Collect all image datablocks"""
        print("\n[Images]")
        for img in bpy.data.images:
            if img.source in ('FILE', 'MOVIE', 'SEQUENCE'):
                if img.packed_file:
                    self.add_packed_file('image', img.name, img, img.filepath)
                else:
                    filepath = bpy.path.abspath(img.filepath, library=img.library)
                    if not filepath:
                        continue
                    
                    category = self.categorize_image(img, filepath)
                    
                    # Handle image sequences
                    if img.source == 'SEQUENCE':
                        sequence_files = self.collect_file_sequence(filepath)
                        for seq_file in sequence_files:
                            self.add_external_file(seq_file, 'image_sequences', {
                                'is_sequence': True,
                                'sequence_base': filepath,
                                'data_block_name': img.name
                            })
                    else:
                        self.add_external_file(filepath, category, {
                            'is_sequence': False,
                            'source': img.source,
                            'data_block_name': img.name
                        })
    
    def categorize_image(self, img, filepath):
        """Categorize image files - prioritize extension check"""
        if not filepath:
            return 'textures'
        
        ext = Path(filepath).suffix.lower()
        
        # Video extensions
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', 
                     '.wmv', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogg', 
                     '.ogv', '.qt', '.mxf', '.dv', '.m2v', '.m2ts', '.ts'}
        
        if ext in video_exts:
            print(f"    🎥 Video texture: {Path(filepath).name}")
            return 'videos'
        
        if hasattr(img, 'source') and img.source == 'MOVIE':
            return 'videos'
        
        if img.source == 'SEQUENCE':
            return 'image_sequences'
        
        if ext in {'.hdr', '.exr'}:
            return 'hdris'
        
        return 'textures'
    
    def collect_file_sequence(self, filepath):
        """Collect all files in a sequence"""
        if not filepath or not os.path.exists(filepath):
            return [filepath] if filepath else []
        
        import re
        
        path_obj = Path(filepath)
        directory = path_obj.parent
        filename = path_obj.stem
        extension = path_obj.suffix
        
        # Find frame numbers (3+ consecutive digits)
        matches = list(re.finditer(r'\d{3,}', filename))
        
        if not matches:
            return [filepath]
        
        # Use last match as frame number
        frame_match = matches[-1]
        frame_str = frame_match.group()
        frame_start = frame_match.start()
        frame_end = frame_match.end()
        
        prefix = filename[:frame_start]
        suffix = filename[frame_end:]
        num_digits = len(frame_str)
        
        # Find all matching files
        sequence_files = []
        
        for potential_file in directory.iterdir():
            if not potential_file.is_file() or potential_file.suffix != extension:
                continue
            
            pot_stem = potential_file.stem
            
            if pot_stem.startswith(prefix) and pot_stem.endswith(suffix):
                middle = pot_stem[len(prefix):len(pot_stem)-len(suffix)] if suffix else pot_stem[len(prefix):]
                
                if middle.isdigit() and len(middle) == num_digits:
                    sequence_files.append(str(potential_file))
        
        sequence_files.sort()
        
        if len(sequence_files) > 1:
            print(f"    📹 Sequence: {prefix}####.{extension} ({len(sequence_files)} frames)")
            return sequence_files
        
        return [filepath]
    
    def collect_movie_clips(self):
        """Collect movie clip datablocks"""
        print("\n[Movie Clips]")
        for clip in bpy.data.movieclips:
            filepath = bpy.path.abspath(clip.filepath)
            self.add_external_file(filepath, 'videos', {'data_block_name': clip.name})
    
    def collect_sounds(self):
        """Collect sound datablocks"""
        print("\n[Sounds]")
        for sound in bpy.data.sounds:
            if sound.packed_file:
                self.add_packed_file('sound', sound.name, sound, sound.filepath)
            else:
                filepath = bpy.path.abspath(sound.filepath, library=sound.library)
                self.add_external_file(filepath, 'sounds', {'data_block_name': sound.name})
    
    def collect_fonts(self):
        """Collect font datablocks"""
        print("\n[Fonts]")
        for font in bpy.data.fonts:
            if font.filepath == '<builtin>':
                continue
            if font.packed_file:
                self.add_packed_file('font', font.name, font, font.filepath)
            else:
                filepath = bpy.path.abspath(font.filepath, library=font.library)
                self.add_external_file(filepath, 'fonts', {'data_block_name': font.name})
    
    def collect_texts(self):
        """Collect text datablocks"""
        print("\n[Text Files]")
        for text in bpy.data.texts:
            if not text.is_in_memory and text.filepath:
                filepath = bpy.path.abspath(text.filepath)
                self.add_external_file(filepath, 'texts', {'data_block_name': text.name})
    
    def collect_volumes(self):
        """Collect VDB volume files"""
        print("\n[Volumes (VDB)]")
        for obj in bpy.data.objects:
            if obj.type == 'VOLUME':
                if hasattr(obj.data, 'filepath') and obj.data.filepath:
                    filepath = bpy.path.abspath(obj.data.filepath)
                    
                    # Check for sequences
                    if self.is_file_sequence(filepath):
                        sequence_files = self.collect_file_sequence(filepath)
                        for seq_file in sequence_files:
                            self.add_external_file(seq_file, 'vdbs', {
                                'is_sequence': True,
                                'sequence_base': filepath,
                                'data_block_name': obj.name
                            })
                    else:
                        self.add_external_file(filepath, 'vdbs', {
                            'is_sequence': False,
                            'data_block_name': obj.name
                        })
    
    def is_file_sequence(self, filepath):
        """Check if filepath contains frame number pattern"""
        if not filepath or not os.path.exists(filepath):
            return False
        
        import re
        filename = Path(filepath).stem
        return bool(re.search(r'\d{3,}', filename))
    
    def collect_libraries(self):
        """Collect linked library files"""
        print("\n[Linked Libraries]")
        for lib in bpy.data.libraries:
            filepath = bpy.path.abspath(lib.filepath)
            self.add_external_file(filepath, 'libraries', {'data_block_name': lib.name})
    
    def collect_cache_files(self):
        """Collect cache files"""
        print("\n[Cache Files]")
        for cache in bpy.data.cache_files:
            filepath = bpy.path.abspath(cache.filepath)
            
            ext = Path(filepath).suffix.lower()
            if ext == '.abc':
                category = 'alembic'
            elif ext in {'.usd', '.usda', '.usdc', '.usdz'}:
                category = 'usd'
            else:
                category = 'caches'
            
            # Check for sequences
            if self.is_file_sequence(filepath):
                sequence_files = self.collect_file_sequence(filepath)
                for seq_file in sequence_files:
                    self.add_external_file(seq_file, category, {
                        'is_sequence': True,
                        'sequence_base': filepath,
                        'data_block_name': cache.name
                    })
            else:
                self.add_external_file(filepath, category, {
                    'is_sequence': False,
                    'data_block_name': cache.name
                })
    
    def collect_shader_nodes(self):
        """Collect files from shader nodes"""
        print("\n[Shader Nodes]")
        for mat in bpy.data.materials:
            if mat.use_nodes and mat.node_tree:
                self._scan_nodes(mat.node_tree.nodes, 'shader')
    
    def collect_compositor_nodes(self):
        """Collect files from compositor nodes"""
        print("\n[Compositor Nodes]")
        for scene in bpy.data.scenes:
            if scene.use_nodes and scene.node_tree:
                self._scan_nodes(scene.node_tree.nodes, 'compositor')
    
    def collect_geometry_nodes(self):
        """Collect files from geometry nodes"""
        print("\n[Geometry Nodes]")
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group:
                    self._scan_nodes(mod.node_group.nodes, 'geometry')
    
    def collect_world_nodes(self):
        """Collect files from world nodes"""
        print("\n[World Nodes]")
        for world in bpy.data.worlds:
            if world.use_nodes and world.node_tree:
                self._scan_nodes(world.node_tree.nodes, 'world')
    
    def _scan_nodes(self, nodes, context_type):
        """Scan nodes for file references"""
        for node in nodes:
            # Script nodes
            if hasattr(node, 'filepath') and node.filepath:
                filepath = bpy.path.abspath(node.filepath)
                self.add_external_file(filepath, 'scripts', {
                    'node_type': node.type,
                    'context': context_type
                })
            
            # Image texture nodes (including video textures)
            if node.type == 'TEX_IMAGE' and hasattr(node, 'image') and node.image:
                img = node.image
                if img.source in ('FILE', 'MOVIE', 'SEQUENCE') and not img.packed_file:
                    filepath = bpy.path.abspath(img.filepath, library=img.library)
                    if filepath:
                        norm_path = os.path.normpath(filepath)
                        if norm_path not in self.files['external']:
                            category = self.categorize_image(img, filepath)
                            self.add_external_file(filepath, category, {
                                'is_sequence': False,
                                'source': img.source,
                                'data_block_name': img.name,
                                'found_in_node': True
                            })
            
            # IES texture nodes
            if node.type == 'TEX_IES' and hasattr(node, 'filepath') and node.filepath:
                filepath = bpy.path.abspath(node.filepath)
                self.add_external_file(filepath, 'ies', {'node_type': 'IES'})
    
    def print_summary(self):
        """Print collection summary"""
        print("\n" + "="*60)
        print("COLLECTION SUMMARY")
        print("="*60)
        print(f"External files: {len(self.files['external'])}")
        print(f"Packed files: {len(self.files['packed'])}")
        print(f"Missing files: {len(self.files['missing'])}")
        
        if self.files['missing']:
            print("\n⚠️  MISSING FILES:")
            for missing in self.files['missing'][:5]:
                print(f"  - {missing}")
            if len(self.files['missing']) > 5:
                print(f"  ... and {len(self.files['missing']) - 5} more")
        
        # Category breakdown
        categories = {}
        for filepath, (category, metadata) in self.files['external'].items():
            categories[category] = categories.get(category, 0) + 1
        
        print("\nBy category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")
        print("="*60 + "\n")

# ============================================================================
# PACKING TASK
# ============================================================================

class PackingTask:
    """Handles packing process in background thread"""
    
    def __init__(self, blend_path, output_path, file_data):
        self.blend_path = Path(blend_path)
        self.output_path = Path(output_path)
        self.file_data = file_data
        self.error = None
        self.progress = 0.0
        self.status = ""
        self.project_path = None
        self.zip_path = None
        self.temp_dir = None
        self.seven_zip = SevenZipManager()
        
    def execute(self):
        """Main execution"""
        try:
            # Validate
            if self.file_data['missing']:
                missing_name = Path(self.file_data['missing'][0]).name
                self.error = f"Critical file missing: {missing_name}"
                return False
            
            # Phase 1: Setup (5%)
            self.update_progress(5.0, "Setting up project...")
            self.setup_project_structure()
            
            # Phase 2: Copy files (35%)
            self.update_progress(10.0, "Copying assets...")
            path_mapping = self.copy_external_files()
            
            # Phase 3: Extract packed (15%)
            self.update_progress(45.0, "Extracting packed files...")
            self.extract_packed_files(path_mapping)
            
            # Phase 4: Create modified blend (25%)
            self.update_progress(60.0, "Creating portable blend...")
            success = self.create_modified_blend(path_mapping)
            if not success:
                self.error = "Failed to create modified blend file"
                return False
            
            # Phase 5: Verify (5%)
            self.update_progress(85.0, "Verifying...")
            if not self.verify_result():
                print("⚠️  Warning: Some paths may not be fully relinked")
            
            # Phase 6: Archive (10%) - NOW WITH 7-ZIP!
            self.update_progress(90.0, "Creating archive...")
            archive_success = self.create_archive_optimized()
            if not archive_success:
                self.error = "Failed to create archive"
                return False
            
            # Phase 7: Cleanup (5%)
            self.update_progress(95.0, "Cleaning up...")
            self.cleanup()
            
            self.update_progress(100.0, "Complete!")
            return True
            
        except Exception as e:
            import traceback
            self.error = f"{str(e)}\n{traceback.format_exc()}"
            self.cleanup_on_error()
            return False
    
    def update_progress(self, value, message=""):
        """Update progress"""
        self.progress = value
        self.status = message
        if message:
            print(f"[{value:5.1f}%] {message}")
    
    def setup_project_structure(self):
        """Create folder structure"""
        blend_name = self.blend_path.stem
        project_name = f"{blend_name}_blendpack"
        
        # Handle existing folders
        has_files = any(self.output_path.iterdir()) if self.output_path.exists() else False
        
        if has_files:
            counter = 1
            while (self.output_path / f"{project_name}_{counter}").exists():
                counter += 1
            self.project_path = self.output_path / f"{project_name}_{counter}"
        else:
            self.project_path = self.output_path
        
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create assets folder if needed
        if self.file_data['external'] or self.file_data['packed']:
            self.assets_path = self.project_path / "assets"
            self.assets_path.mkdir(exist_ok=True)
            
            self.category_paths = {
                'textures': self.assets_path / "textures",
                'videos': self.assets_path / "videos",
                'sounds': self.assets_path / "sounds",
                'fonts': self.assets_path / "fonts",
                'hdris': self.assets_path / "hdris",
                'vdbs': self.assets_path / "vdbs",
                'image_sequences': self.assets_path / "image_sequences",
                'libraries': self.assets_path / "libraries",
                'caches': self.assets_path / "caches",
                'texts': self.assets_path / "texts",
                'alembic': self.assets_path / "alembic",
                'usd': self.assets_path / "usd",
                'scripts': self.assets_path / "scripts",
                'ies': self.assets_path / "ies",
                'other': self.assets_path / "other",
            }
            
            for folder in self.category_paths.values():
                folder.mkdir(exist_ok=True)
        else:
            self.category_paths = {}
    
    def copy_external_files(self):
        """Copy external files and build path mapping"""
        path_mapping = {}
        external_files = self.file_data['external']
        
        if not external_files:
            return path_mapping
        
        total = len(external_files)
        
        for idx, (old_path, (category, metadata)) in enumerate(external_files.items()):
            try:
                old_path_obj = Path(old_path)
                
                target_dir = self.category_paths.get(category, self.category_paths['other'])
                
                # Create subdirectory
                if len(old_path_obj.parts) > 2:
                    subdir_parts = old_path_obj.parts[-3:-1]
                    subdir_name = "_".join(subdir_parts[:2])
                    subdir_name = "".join(c for c in subdir_name if c.isalnum() or c in "._- ")
                    target_dir = target_dir / subdir_name
                    target_dir.mkdir(parents=True, exist_ok=True)
                
                # Handle name conflicts
                new_path = target_dir / old_path_obj.name
                counter = 1
                while new_path.exists():
                    stem = old_path_obj.stem
                    suffix = old_path_obj.suffix
                    new_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Copy
                shutil.copy2(old_path, new_path)
                path_mapping[old_path] = str(new_path)
                
                # Update progress
                if idx % max(1, total // 10) == 0:
                    progress = 10.0 + (idx + 1) / total * 35.0
                    msg = f"Copying... ({idx+1}/{total})"
                    self.update_progress(progress, msg)
                
            except Exception as e:
                print(f"  ⚠️  Error copying {old_path_obj.name}: {e}")
        
        return path_mapping
    
    def extract_packed_files(self, path_mapping):
        """Extract packed files"""
        if not self.file_data['packed']:
            return
        
        self.temp_dir = tempfile.mkdtemp(prefix="blendpack_")
        total = len(self.file_data['packed'])
        
        for idx, packed_info in enumerate(self.file_data['packed']):
            try:
                file_type = packed_info['type']
                name = packed_info['name']
                data_block = packed_info['data_block']
                
                # Determine category
                if file_type == 'image':
                    ext = Path(name).suffix or '.png'
                    category = 'hdris' if ext.lower() in {'.hdr', '.exr'} else 'textures'
                elif file_type == 'sound':
                    category = 'sounds'
                    ext = Path(name).suffix or '.wav'
                elif file_type == 'font':
                    category = 'fonts'
                    ext = Path(name).suffix or '.ttf'
                else:
                    category = 'other'
                    ext = '.dat'
                
                target_dir = self.category_paths.get(category, self.category_paths['other'])
                
                # Create filename
                safe_name = "".join(c for c in Path(name).stem if c.isalnum() or c in "._- ")
                if not safe_name:
                    safe_name = f"packed_{file_type}"
                
                new_path = target_dir / f"{safe_name}{ext}"
                counter = 1
                while new_path.exists():
                    new_path = target_dir / f"{safe_name}_{counter}{ext}"
                    counter += 1
                
                # Extract
                if hasattr(data_block, 'packed_file') and data_block.packed_file:
                    if file_type == 'image':
                        temp_file = Path(self.temp_dir) / f"temp_{idx}{ext}"
                        data_block.filepath_raw = str(temp_file)
                        data_block.save()
                        if temp_file.exists():
                            shutil.move(str(temp_file), str(new_path))
                    else:
                        packed_data = data_block.packed_file.data
                        new_path.write_bytes(bytes(packed_data))
                    
                    # Map
                    if packed_info['original_filepath']:
                        original_abs = str(self.blend_path.parent / packed_info['original_filepath'].replace('//', ''))
                        path_mapping[os.path.normpath(original_abs)] = str(new_path)
                    
                    print(f"  ✓ Extracted: {name}")
                
                if idx % max(1, total // 5) == 0:
                    progress = 45.0 + (idx + 1) / total * 15.0
                    msg = f"Extracting... ({idx+1}/{total})"
                    self.update_progress(progress, msg)
                
            except Exception as e:
                print(f"  ⚠️  Error extracting: {e}")
    
    def create_modified_blend(self, path_mapping):
        """Create modified blend using robust relinking"""
        # Copy blend
        dest_blend = self.project_path / f"{self.blend_path.stem}_clone.blend"
        shutil.copy2(self.blend_path, dest_blend)
        
        # Build a RELATIVE path mapping
        relative_mapping = {}
        
        print("\n" + "="*60)
        print("BUILDING PATH MAPPING FOR CLONE")
        print("="*60)
        print(f"Original blend: {self.blend_path}")
        print(f"Clone blend: {dest_blend}")
        
        for old_abs_path, new_abs_path in path_mapping.items():
            # Calculate what the relative path WAS in the original
            try:
                old_rel_from_original = os.path.relpath(old_abs_path, self.blend_path.parent)
                old_rel_blender = "//" + old_rel_from_original.replace("\\", "/")
            except:
                old_rel_blender = old_abs_path
            
            # Calculate what the relative path SHOULD BE in the clone
            try:
                new_rel_from_clone = os.path.relpath(new_abs_path, dest_blend.parent)
                new_rel_blender = "//" + new_rel_from_clone.replace("\\", "/")
            except:
                new_rel_blender = new_abs_path
            
            # Store BOTH mappings
            relative_mapping[os.path.normpath(old_abs_path)] = new_rel_blender
            relative_mapping[old_rel_blender] = new_rel_blender
            
            print(f"  {old_rel_blender}")
            print(f"    -> {new_rel_blender}")
        
        print("="*60 + "\n")
        
        # Save mapping to JSON
        mapping_file = self.project_path / "path_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump({
                'project_path': str(self.project_path),
                'clone_blend_path': str(dest_blend),
                'mapping': relative_mapping
            }, f, indent=2)
        
        # Generate script
        script = self.generate_relink_script(mapping_file)
        script_path = self.project_path / "relink_script.py"
        script_path.write_text(script, encoding='utf-8')
        
        # Run Blender subprocess
        blender_exe = bpy.app.binary_path
        cmd = [
            str(blender_exe),
            str(dest_blend),
            '--background',
            '--python', str(script_path)
        ]
        
        print(f"\nRunning: {' '.join(cmd)}\n")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='replace'
            )
            
            # Cleanup
            script_path.unlink()
            mapping_file.unlink()
            
            if result.returncode != 0:
                print(f"Subprocess error:\n{result.stderr}")
                print(f"Subprocess output:\n{result.stdout}")
                return False
            
            print("✓ Relinking completed!")
            return True
            
        except subprocess.TimeoutExpired:
            self.error = "Relinking timed out"
            return False
        except Exception as e:
            self.error = f"Subprocess failed: {e}"
            return False
    
    def generate_relink_script(self, mapping_file):
        """Generate comprehensive relinking script"""
        script = f'''import bpy
import os
import json
from pathlib import Path

# Load mapping
with open(r"{str(mapping_file)}", 'r', encoding='utf-8') as f:
    data = json.load(f)

project_path = Path(data['project_path'])
clone_blend_path = Path(data['clone_blend_path'])
path_mapping = data['mapping']

print("="*60)
print("RELINKING ALL ASSETS")
print("="*60)
print(f"Project: {{project_path}}")
print(f"Clone: {{clone_blend_path}}")
print(f"Mappings: {{len(path_mapping)}}")

def normalize_path(path):
    """Normalize path for comparison"""
    if not path:
        return ""
    try:
        # Handle both absolute and relative paths
        if path.startswith("//"):
            # Relative path - resolve from blend file location
            rel_part = path[2:].replace("/", os.sep)
            abs_path = os.path.join(os.path.dirname(bpy.data.filepath), rel_part)
            return os.path.normpath(abs_path)
        else:
            # Absolute path
            abs_path = bpy.path.abspath(path)
            return os.path.normpath(abs_path)
    except:
        return os.path.normpath(path)

def relink_path(old_path):
    """Relink a path using multiple matching strategies"""
    if not old_path:
        return None
    
    # Strategy 1: Try the path as-is
    if old_path in path_mapping:
        return path_mapping[old_path]
    
    # Strategy 2: Try normalized absolute path
    norm_abs = normalize_path(old_path)
    if norm_abs in path_mapping:
        return path_mapping[norm_abs]
    
    # Strategy 3: Try with forward slashes
    old_path_forward = old_path.replace("\\\\", "/")
    if old_path_forward in path_mapping:
        return path_mapping[old_path_forward]
    
    return None

stats = {{
    'images': 0,
    'clips': 0,
    'sounds': 0,
    'fonts': 0,
    'texts': 0,
    'volumes': 0,
    'libraries': 0,
    'caches': 0
}}

# Relink Images
print("\\n[Images]")
for img in bpy.data.images:
    if img.source in ('FILE', 'MOVIE', 'SEQUENCE') and not img.packed_file:
        old_path = img.filepath
        new_path = relink_path(old_path)
        if new_path:
            img.filepath = new_path
            stats['images'] += 1
            print(f"  ✓ {{img.name}}: {{old_path}} -> {{new_path}}")
        else:
            print(f"  ✗ {{img.name}}: No mapping for {{old_path}}")

# Relink Movie Clips
print("\\n[Movie Clips]")
for clip in bpy.data.movieclips:
    old_path = clip.filepath
    new_path = relink_path(old_path)
    if new_path:
        clip.filepath = new_path
        stats['clips'] += 1
        print(f"  ✓ {{clip.name}}: {{old_path}} -> {{new_path}}")

# Relink Sounds
print("\\n[Sounds]")
for sound in bpy.data.sounds:
    if not sound.packed_file:
        old_path = sound.filepath
        new_path = relink_path(old_path)
        if new_path:
            sound.filepath = new_path
            stats['sounds'] += 1
            print(f"  ✓ {{sound.name}}")

# Relink Fonts
print("\\n[Fonts]")
for font in bpy.data.fonts:
    if not font.packed_file and font.filepath != '<builtin>':
        old_path = font.filepath
        new_path = relink_path(old_path)
        if new_path:
            font.filepath = new_path
            stats['fonts'] += 1
            print(f"  ✓ {{font.name}}")

# Relink Text Files
print("\\n[Text Files]")
for text in bpy.data.texts:
    if not text.is_in_memory and text.filepath:
        old_path = text.filepath
        new_path = relink_path(old_path)
        if new_path:
            text.filepath = new_path
            stats['texts'] += 1
            print(f"  ✓ {{text.name}}")

# Relink Volumes
print("\\n[Volumes]")
for obj in bpy.data.objects:
    if obj.type == 'VOLUME':
        if hasattr(obj.data, 'filepath') and obj.data.filepath:
            old_path = obj.data.filepath
            new_path = relink_path(old_path)
            if new_path:
                obj.data.filepath = new_path
                stats['volumes'] += 1
                print(f"  ✓ {{obj.name}}: {{old_path}} -> {{new_path}}")
            else:
                print(f"  ✗ {{obj.name}}: No mapping for {{old_path}}")

# Relink Libraries
print("\\n[Libraries]")
for lib in bpy.data.libraries:
    old_path = lib.filepath
    new_path = relink_path(old_path)
    if new_path:
        lib.filepath = new_path
        stats['libraries'] += 1
        print(f"  ✓ {{lib.name}}")

# Relink Cache Files
print("\\n[Cache Files]")
for cache in bpy.data.cache_files:
    old_path = cache.filepath
    new_path = relink_path(old_path)
    if new_path:
        cache.filepath = new_path
        stats['caches'] += 1
        print(f"  ✓ {{cache.name}}")

# Save
print("\\n[Saving]")
bpy.ops.wm.save_mainfile()
print("✓ Saved!")

print("\\n" + "="*60)
print("RELINKING SUMMARY")
print("="*60)
for key, value in stats.items():
    if value > 0:
        print(f"  {{key}}: {{value}}")
print("="*60)
'''
        return script
    
    def verify_result(self):
        """Verify packed project"""
        print("\n" + "="*60)
        print("VERIFYING")
        print("="*60)
        
        clone_blend = self.project_path / f"{self.blend_path.stem}_clone.blend"
        if not clone_blend.exists():
            print("✗ Clone not found")
            return False
        
        print("✓ Clone exists")
        
        if self.file_data['external'] or self.file_data['packed']:
            if not self.assets_path.exists():
                print("✗ Assets folder missing")
                return False
            print("✓ Assets folder exists")
        
        total = 0
        for category, path in self.category_paths.items():
            if path.exists():
                count = sum(1 for f in path.rglob('*') if f.is_file())
                if count > 0:
                    print(f"  {category}: {count}")
                    total += count
        
        print(f"✓ Total assets: {total}")
        print("="*60)
        return True
    
    def create_archive_optimized(self):
        """Create archive using 7-Zip with fallback to zipfile"""
        project_name = self.project_path.name if self.project_path != self.output_path else f"{self.blend_path.stem}_blendpack"
        self.zip_path = self.output_path / f"{project_name}.zip"
        
        print("\n" + "="*60)
        print("CREATING ARCHIVE")
        print("="*60)
        print(f"Method: {'7-Zip' if self.seven_zip.use_7zip else 'Python zipfile'}")
        print(f"Output: {self.zip_path}")
        print("="*60 + "\n")
        
        # Try 7-Zip first
        if self.seven_zip.use_7zip:
            success, error = self.seven_zip.compress(
                self.project_path,
                self.zip_path,
                progress_callback=self.update_progress
            )
            
            if success:
                final_size = self.zip_path.stat().st_size
                print(f"\n✓ 7-Zip compression successful!")
                print(f"  Archive size: {final_size / (1024*1024):.2f} MB")
                return True
            else:
                print(f"\n⚠️  7-Zip failed: {error}")
                print("Falling back to Python zipfile...")
        
        # Fallback to Python zipfile
        return self.create_archive_fallback()
    
    def create_archive_fallback(self):
        """Fallback archive creation using Python zipfile"""
        project_name = self.project_path.name if self.project_path != self.output_path else f"{self.blend_path.stem}_blendpack"
        self.zip_path = self.output_path / f"{project_name}.zip"
        temp_zip = self.output_path / f"{project_name}_temp.zip"
        
        try:
            # Collect all files first
            print("\n[Collecting files for archive...]")
            files = []
            total_size = 0
            
            for root, dirs, filenames in os.walk(self.project_path):
                for filename in filenames:
                    file_path = Path(root) / filename
                    # Don't include the zip file itself
                    if file_path.absolute() != self.zip_path.absolute() and file_path.absolute() != temp_zip.absolute():
                        try:
                            file_size = file_path.stat().st_size
                            files.append((file_path, file_size))
                            total_size += file_size
                        except OSError as e:
                            print(f"  ⚠️  Warning: Could not stat {file_path.name}: {e}")
            
            total_files = len(files)
            print(f"  Files to archive: {total_files}")
            print(f"  Total size: {total_size / (1024*1024):.2f} MB")
            
            # Create zip with progress tracking
            processed_size = 0
            last_progress = 90.0
            
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as zipf:
                for idx, (file_path, file_size) in enumerate(files):
                    try:
                        arcname = file_path.relative_to(self.project_path)
                        zipf.write(file_path, arcname)
                        
                        processed_size += file_size
                        
                        # Update progress based on size processed
                        if total_size > 0:
                            size_progress = (processed_size / total_size) * 5.0  # 5% of total progress
                            current_progress = 90.0 + size_progress
                            
                            # Only update if progress changed significantly
                            if current_progress - last_progress >= 0.5:
                                msg = f"Archiving... ({idx+1}/{total_files})"
                                self.update_progress(current_progress, msg)
                                last_progress = current_progress
                        
                    except Exception as e:
                        print(f"  ⚠️  Warning: Could not add {file_path.name} to archive: {e}")
            
            # Replace old zip with new one atomically
            if self.zip_path.exists():
                self.zip_path.unlink()
            temp_zip.rename(self.zip_path)
            
            # Update progress immediately after completion
            self.update_progress(95.0, "Archive complete!")
            
            final_size = self.zip_path.stat().st_size
            print(f"\n✓ Archive created: {self.zip_path}")
            print(f"  Compressed size: {final_size / (1024*1024):.2f} MB")
            print(f"  Compression ratio: {(1 - final_size/total_size)*100:.1f}%" if total_size > 0 else "")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Archive creation failed: {e}")
            if temp_zip.exists():
                try:
                    temp_zip.unlink()
                except:
                    pass
            return False
    
    def cleanup(self):
        """Cleanup temp files"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            if self.project_path and self.project_path != self.output_path:
                if self.project_path.exists():
                    shutil.rmtree(self.project_path)
                    print("✓ Cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def cleanup_on_error(self):
        """Cleanup on error"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            if self.project_path and self.project_path.exists():
                if self.project_path != self.output_path:
                    shutil.rmtree(self.project_path)
            if self.zip_path and self.zip_path.exists():
                self.zip_path.unlink()
        except:
            pass

# ============================================================================
# OPERATORS
# ============================================================================

class BLENDPACK_OT_select_folder(Operator):
    bl_idname = "blendpack.select_folder"
    bl_label = "Select Folder"
    bl_description = "Select output folder"
    bl_options = {'INTERNAL'}
    
    directory: StringProperty(subtype='DIR_PATH')
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        context.scene.blendpack_props.output_path = self.directory
        context.scene.blendpack_props.error_message = ""
        return {'FINISHED'}


class BLENDPACK_OT_start_packing(Operator):
    bl_idname = "blendpack.start_packing"
    bl_label = "Start Packing"
    bl_description = "Pack all assets"
    
    _timer = None
    _thread = None
    _task = None
    _hide_timer = None
    
    def modal(self, context, event):
        """Modal handler"""
        if event.type == 'TIMER':
            props = context.scene.blendpack_props
            
            # Hide progress bar
            if self._hide_timer:
                props.show_progress = False
                props.progress = 0.0
                props.status_message = ""
                context.window_manager.event_timer_remove(self._hide_timer)
                self._hide_timer = None
                return {'FINISHED'}
            
            # Update from task
            if self._task and self._thread:
                props.progress = self._task.progress
                props.status_message = self._task.status
                
                # Check if done
                if not self._thread.is_alive():
                    wm = context.window_manager
                    wm.event_timer_remove(self._timer)
                    self._timer = None
                    
                    if self._task.error:
                        props.error_message = self._task.error
                        props.is_processing = False
                        props.show_progress = False
                        props.status_message = ""
                        self.report({'ERROR'}, f"Failed: {self._task.error}")
                        return {'CANCELLED'}
                    else:
                        props.is_processing = False
                        self.report({'INFO'}, f"Packed: {self._task.zip_path}")
                        
                        # Hide after 3s
                        self._hide_timer = wm.event_timer_add(3.0, window=context.window)
                        return {'RUNNING_MODAL'}
            
            # Redraw
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        props = context.scene.blendpack_props
        
        # Validate
        if props.is_processing:
            self.report({'WARNING'}, "Already processing")
            return {'CANCELLED'}
        
        if not props.output_path or not os.path.isdir(props.output_path):
            props.error_message = "Select valid output folder"
            return {'CANCELLED'}
        
        blend_path = bpy.data.filepath
        if not blend_path:
            props.error_message = "Save blend file first"
            return {'CANCELLED'}
        
        # Reset
        props.error_message = ""
        props.progress = 0.0
        props.status_message = ""
        props.show_progress = True
        props.is_processing = True
        
        # Collect files
        print("\n" + "="*60)
        print("BLENDPACK v2.1 - STARTING")
        print("="*60)
        print(f"Blend: {blend_path}")
        print(f"Output: {props.output_path}")
        
        try:
            collector = FileCollector(blend_path)
            file_data = collector.collect_all()
        except Exception as e:
            props.error_message = f"Collection failed: {str(e)}"
            props.is_processing = False
            props.show_progress = False
            return {'CANCELLED'}
        
        # Create task
        self._task = PackingTask(blend_path, props.output_path, file_data)
        
        # Start thread
        self._thread = threading.Thread(target=self._task.execute, daemon=True)
        self._thread.start()
        
        # Start modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        """Cancel handler"""
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        if self._hide_timer:
            context.window_manager.event_timer_remove(self._hide_timer)

# ============================================================================
# UI
# ============================================================================

class BLENDPACK_PT_main_panel(Panel):
    bl_label = "Blendpack"
    bl_idname = "BLENDPACK_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Blendpack'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        layout.scale_x = 1.5
        
        props = context.scene.blendpack_props
        
        # Header
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Blendpack", icon='PACKAGE')
        col.separator(factor=0.5)
        
        # Description
        desc = box.column(align=True)
        desc.scale_y = 0.8
        desc.label(text="Pack all external assets with your")
        desc.label(text="blend file for easy sharing without")
        desc.label(text="missing files.")
        
        box.separator(factor=0.5)
        
        # Credits
        credit = box.column(align=True)
        credit.scale_y = 0.7
        credit.label(text="Created by Cloud Blender Render")
        credit.label(text="Get RTX 5090 for $0.69/hour")
        
        # Link
        row = box.row()
        row.scale_y = 0.8
        row.operator("wm.url_open", text="Learn More", icon='URL').url = "https://cloud-blender-render.rahulahire.com/"
        
        layout.separator()
        
        # Output selector
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Output Folder:")
        
        sub = col.column(align=True)
        sub.enabled = False
        if props.output_path:
            sub.label(text=props.output_path, icon='FOLDER_REDIRECT')
        else:
            sub.label(text="No folder selected", icon='FOLDER_REDIRECT')
        
        col.operator("blendpack.select_folder", text="Select Folder", icon='FILEBROWSER')
        
        layout.separator()
        
        # Start button
        row = layout.row()
        row.scale_y = 1.5
        row.enabled = not props.is_processing
        if props.is_processing:
            row.operator("blendpack.start_packing", text="Processing...", icon='TIME')
        else:
            row.operator("blendpack.start_packing", text="Start Packing", icon='EXPORT')
        
        # Progress
        if props.show_progress:
            box = layout.box()
            col = box.column(align=True)
            col.prop(props, "progress", text="Progress", slider=True)
            if props.status_message:
                col.label(text=props.status_message, icon='INFO')
        
        # Error
        if props.error_message:
            box = layout.box()
            col = box.column(align=True)
            col.alert = True
            col.scale_y = 0.7
            col.label(text="Error:", icon='ERROR')
            lines = props.error_message.split('\n')
            for line in lines[:5]:
                words = line.split()
                text_line = ""
                for word in words:
                    if len(text_line + word) > 40:
                        col.label(text=text_line)
                        text_line = word + " "
                    else:
                        text_line += word + " "
                if text_line:
                    col.label(text=text_line.strip())

# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    BlendpackProperties,
    BLENDPACK_OT_select_folder,
    BLENDPACK_OT_start_packing,
    BLENDPACK_PT_main_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.blendpack_props = bpy.props.PointerProperty(type=BlendpackProperties)
    
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)
    
    print("Blendpack v2.1 registered")

def unregister():
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    if hasattr(bpy.types.Scene, 'blendpack_props'):
        del bpy.types.Scene.blendpack_props
    
    print("Blendpack v2.1 unregistered")

if __name__ == "__main__":
    register()