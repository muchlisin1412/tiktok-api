from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import re
from urllib.parse import urlparse, parse_qs
import requests

app = Flask(__name__)
CORS(app)

# Directory untuk temporary files
UPLOAD_FOLDER = 'downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class TikTokDownloader:
    def __init__(self):
        self.ydl_opts = {
            'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
            'format': 'best[height<=720]',
        }
    
    def extract_tiktok_info(self, url):
        """Extract video info dari TikTok URL"""
        try:
            # yt-dlp options untuk TikTok
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    info = info['entries'][0]
                
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'author': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'filesize': info.get('filesize', 0)
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def download_video(self, url, quality='720p'):
        """Download video tanpa watermark"""
        try:
            ydl_opts = {
                'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
            }
            
            if quality == '720p':
                ydl_opts['format'] = 'best[height<=720]'
            elif quality == '480p':
                ydl_opts['format'] = 'best[height<=480]'
            else:
                ydl_opts['format'] = 'best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if 'entries' in info:
                    info = info['entries'][0]
                
                filename = ydl.prepare_filename(info)
                return {
                    'success': True,
                    'filename': filename,
                    'title': info.get('title', 'video')
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Initialize downloader
downloader = TikTokDownloader()

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'TikTok Downloader API v1.0',
        'endpoints': {
            'GET /info?url=<tiktok_url>': 'Get video info',
            'POST /download': 'Download video',
            'GET /file/<filename>': 'Serve downloaded file'
        }
    })

@app.route('/info', methods=['GET'])
def get_info():
    """Get video information"""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter required'}), 400
    
    info = downloader.extract_tiktok_info(url)
    return jsonify(info)

@app.route('/download', methods=['POST'])
def download():
    """Download video"""
    data = request.get_json()
    url = data.get('url') if data else request.form.get('url')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    quality = data.get('quality', '720p') if data else '720p'
    result = downloader.download_video(url, quality)
    
    if result['success']:
        return jsonify({
            'success': True,
            'filename': os.path.basename(result['filename']),
            'download_url': f'/file/{os.path.basename(result["filename"])}'
        })
    else:
        return jsonify(result), 500

@app.route('/file/<filename>')
def serve_file(filename):
    """Serve downloaded file"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/audio', methods=['POST'])
def download_audio():
    """Download audio only"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            
        return jsonify({
            'success': True,
            'filename': os.path.basename(filename),
            'download_url': f'/file/{os.path.basename(filename)}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
