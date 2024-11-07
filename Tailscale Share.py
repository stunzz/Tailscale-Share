import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import json
import re
import os
import threading
import time

class TailscaleFileSender:
    def __init__(self, root):
        self.root = root
        self.root.title("Tailscale Share")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        # Configure dark theme colors
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#007acc',
            'hover': '#1f77d0',
            'button_bg': '#2d2d2d',
            'entry_bg': '#2d2d2d',
            'border': '#3d3d3d',
            'success': '#4caf50',
            'error': '#f44336',
            'warning': '#ff9800',
            'button_text': '#000000'
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        # Apply custom styles
        self.setup_styles()
        
        # Main container
        main_container = tk.Frame(root, bg=self.colors['bg'], padx=20, pady=20)
        main_container.pack(fill=tk.BOTH, expand=True)

        # File selection section
        file_section = tk.LabelFrame(main_container, text="File Selection", 
                                   bg=self.colors['bg'], fg=self.colors['fg'],
                                   padx=10, pady=10)
        file_section.pack(fill=tk.X, pady=(0, 15))
        
        self.file_entry = tk.Entry(file_section, width=45,
                                 bg=self.colors['entry_bg'], 
                                 fg=self.colors['fg'],
                                 insertbackground=self.colors['fg'])
        self.file_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        browse_button = ttk.Button(file_section, text="Browse", 
                                 style='Accent.TButton',
                                 command=self.browse_file,
                                 width=10)
        browse_button.pack(side=tk.LEFT)

        # Device selection section
        device_section = tk.LabelFrame(main_container, text="Device Selection", 
                                     bg=self.colors['bg'], fg=self.colors['fg'],
                                     padx=10, pady=10)
        device_section.pack(fill=tk.X, pady=(0, 15))
        
        device_frame = tk.Frame(device_section, bg=self.colors['bg'])
        device_frame.pack(fill=tk.X)
        
        self.device_dropdown = ttk.Combobox(device_frame, width=45,
                                          style='Custom.TCombobox',
                                          state="readonly")
        self.device_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_button = ttk.Button(device_frame, text="🔄", 
                                  style='Accent.TButton',
                                  command=self.populate_devices,
                                  width=3)
        refresh_button.pack(side=tk.LEFT)

        # Status section
        self.status_label = tk.Label(main_container, text="", 
                                   bg=self.colors['bg'], fg=self.colors['fg'])
        self.status_label.pack(pady=(0, 15))

        # Progress section
        self.progress_frame = tk.LabelFrame(main_container, text="Transfer Status",
                                          bg=self.colors['bg'], fg=self.colors['fg'],
                                          padx=10, pady=10)
        self.progress_frame.pack_forget()
        
        self.progress_detail_label = tk.Label(self.progress_frame, text="",
                                            bg=self.colors['bg'], fg=self.colors['fg'])
        self.progress_detail_label.pack(pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=400, 
                                          mode='indeterminate',
                                          style='Custom.Horizontal.TProgressbar')
        self.progress_bar.pack()

        # Send button section
        send_button = ttk.Button(main_container, text="Send Files",
                               style='Accent.TButton',
                               command=self.send_files_with_progress,
                               width=15)
        send_button.pack(pady=15)

        # Get current device's IP
        self.current_device_ip = self.get_current_device_ip()

        # Populate devices with a delay
        self.root.after(1000, self.populate_devices)

        self.files = []

    def setup_styles(self):
        """Configure custom styles for widgets"""
        style = ttk.Style()
        
        # Configure progress bar style
        style.configure('Custom.Horizontal.TProgressbar',
                       troughcolor=self.colors['bg'],
                       background=self.colors['accent'])
        
        # Configure button style with black text
        style.configure('Accent.TButton',
                       background=self.colors['accent'],
                       foreground=self.colors['button_text'])
        
        # Map hover state for buttons
        style.map('Accent.TButton',
                 background=[('active', self.colors['hover'])],
                 foreground=[('active', self.colors['button_text'])])
        
        # Configure combobox style
        style.configure('Custom.TCombobox',
                       fieldbackground=self.colors['entry_bg'],
                       background=self.colors['entry_bg'],
                       foreground=self.colors['fg'],
                       selectbackground=self.colors['accent'],
                       selectforeground=self.colors['fg'])

    def get_current_device_ip(self):
        """Retrieve the current device's Tailscale IP."""
        try:
            result = subprocess.run(['tailscale', 'ip', '-4'], 
                                    capture_output=True, 
                                    text=True, 
                                    timeout=5)
            
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def browse_file(self):
        """Open file browser to select multiple files."""
        file_paths = filedialog.askopenfilenames()
        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, ", ".join(file_paths))
        self.files = file_paths

    def populate_devices(self):
        """Fetch and populate online Tailscale devices using multiple methods."""
        self.status_label.config(text="Refreshing device list...", fg=self.colors['accent'])
        self.root.update()
        
        online_devices = []

        # Method 1: Try JSON status
        try:
            result = subprocess.run(['tailscale', 'status', '--json'], 
                                    capture_output=True, 
                                    text=True, 
                                    timeout=5)
            
            if result.returncode == 0:
                try:
                    status = json.loads(result.stdout)
                    for peer in status.get('Peers', []):
                        if (peer.get('Online', False) or 
                            peer.get('Connected') == '-' or 
                            peer.get('Connected') is None):
                            device_name = peer.get('HostName', peer.get('Name', 'Unknown'))
                            device_ip = peer.get('TailscaleIP', peer.get('IP', 'N/A'))
                            
                            if device_ip != self.current_device_ip:
                                online_devices.append((f"{device_name} ({device_ip})", device_ip))
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        # Method 2: Fall back to text-based status parsing
        if not online_devices:
            try:
                result = subprocess.run(['tailscale', 'status'], 
                                        capture_output=True, 
                                        text=True, 
                                        timeout=5)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'offline' not in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[0]
                                device_name = parts[1]
                                
                                if ip != self.current_device_ip:
                                    online_devices.append((f"{device_name} ({ip})", ip))
            except Exception:
                pass

        # Update UI based on results
        if online_devices:
            current_selection = self.device_dropdown.get()
            self.device_dropdown['values'] = [device[0] for device in online_devices]
            self.device_ips = dict(online_devices)
            
            if current_selection and current_selection in self.device_dropdown['values']:
                self.device_dropdown.set(current_selection)
            else:
                self.device_dropdown.current(0)
            
            self.status_label.config(text=f"Found {len(online_devices)} online devices", 
                                   fg=self.colors['success'])
        else:
            self.status_label.config(text="No online Tailscale devices found", 
                                   fg=self.colors['error'])
            self.device_dropdown['values'] = []
            messagebox.showwarning("No Devices", 
                                 "No online Tailscale devices found. Ensure Tailscale is running and devices are online.")

    def send_files_with_progress(self):
        """Send multiple files with progress indication."""
        file_paths = self.files
        selected_device = self.device_dropdown.get()
        ip_address = self.device_ips.get(selected_device)

        if not file_paths:
            messagebox.showerror("Error", "Please select one or more files to send.")
            return

        if not ip_address:
            messagebox.showerror("Error", "Please select a recipient device.")
            return

        self.progress_frame.pack(fill=tk.X, pady=(0, 15))
        self.progress_detail_label.config(text="Transferring files...",
                                         fg=self.colors['accent'])
        self.progress_bar.start(10)

        def run_transfers():
            total_files = len(file_paths)
            completed_files = 0

            for file_path in file_paths:
                try:
                    command = f'tailscale file cp "{file_path}" {ip_address}:'
                    process = subprocess.Popen(
                        command, 
                        shell=True, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0:
                        completed_files += 1
                        self.root.after(0, self.update_progress, 
                                        completed_files, total_files)
                    else:
                        self.root.after(0, self.transfer_failed, 
                                        f"Failed to send file '{os.path.basename(file_path)}':\n{stderr}")
                
                except Exception as e:
                    self.root.after(0, self.transfer_failed, 
                                    f"An error occurred while sending '{os.path.basename(file_path)}':\n{e}")

            if completed_files == total_files:
                self.root.after(0, self.transfer_complete, 
                                f"All {total_files} files sent successfully to {selected_device}!")

        threading.Thread(target=run_transfers, daemon=True).start()

    def update_progress(self, completed, total):
        """Update the progress display for multiple file transfers."""
        self.progress_detail_label.config(text=f"Transferred {completed}/{total} files")

    def transfer_complete(self, message):
        """Handle successful multiple file transfer."""
        self.progress_bar.stop()
        messagebox.showinfo("Success", message)
        self.progress_detail_label.config(text="Transfer Complete!", 
                                         fg=self.colors['success'])
        self.root.after(3000, self.progress_frame.pack_forget)

    def transfer_failed(self, error_message):
        """Handle file transfer failure."""
        self.progress_bar.stop()
        messagebox.showerror("Error", error_message)
        self.progress_detail_label.config(text="Transfer Failed", 
                                         fg=self.colors['error'])
        self.root.after(3000, self.progress_frame.pack_forget)

def main():
    root = tk.Tk()
    app = TailscaleFileSender(root)
    root.mainloop()

if __name__ == "__main__":
    main()
