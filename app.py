from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import re
import json
import os
import string
import glob
import sys

# --- PHẦN 1: KHỞI TẠO ỨNG DỤNG FLASK ---
app = Flask(__name__)

# --- PHẦN 2: CÁC HÀM TIỆN ÍCH ---
def parse_quiz_from_content(content: str) -> list:
    """Phân tích nội dung markdown từ một chuỗi thay vì một tệp."""
    blocks = re.split(r'(\n\s*\*\*\d+\.\s*)', content)
    full_blocks = [blocks[i] + blocks[i+1] for i in range(1, len(blocks)-1, 2)]
    if blocks and blocks[0].strip().startswith('**'):
        full_blocks.insert(0, blocks[0])
    parser_regex = re.compile(
        r"\*\*(\d+)\.\s*(?P<question>.*?)\*\*\s*"
        r"(?P<options>(?:^[A-D]\..*$\n?)+)"
        r"đáp án:\s*(?P<answer>[A-D])\s*"
        r"Giải thích:\s*(?P<explanation>.*)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    option_regex = re.compile(r"^(?P<key>[A-D])\.\s*(?P<value>.*)$", re.MULTILINE)
    quiz_data = []
    for block in full_blocks:
        match = parser_regex.search(block)
        if match:
            data = match.groupdict()
            options_dict = {
                opt_match.group('key'): opt_match.group('value').strip()
                for opt_match in option_regex.finditer(data['options'])
            }
            quiz_data.append({
                "id": int(match.group(1)),
                "question": data['question'].strip(),
                "options": options_dict,
                "answer": data['answer'].strip().upper(),
                "explanation": data['explanation'].strip()
            })
    return quiz_data

def sanitize_filename(name: str) -> str:
    """Chuẩn hóa chuỗi thành tên tệp hợp lệ."""
    sanitized = name.lower()
    sanitized = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', sanitized)
    sanitized = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', sanitized)
    sanitized = re.sub(r'[ìíịỉĩ]', 'i', sanitized)
    sanitized = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', sanitized)
    sanitized = re.sub(r'[ùúụủũưừứựửữ]', 'u', sanitized)
    sanitized = re.sub(r'[ỳýỵỷỹ]', 'y', sanitized)
    sanitized = re.sub(r'[đ]', 'd', sanitized)
    sanitized = re.sub(r'\s+', '_', sanitized)
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    sanitized = ''.join(c for c in sanitized if c in valid_chars)
    return sanitized

# --- PHẦN 3: CÁC ROUTE CỦA MÁY CHỦ WEB ---
@app.route('/')
def index():
    """Hiển thị trang chủ để tạo bài trắc nghiệm và liệt kê các bài đã có."""
    root_dir = os.getcwd() # Sử dụng thư mục làm việc hiện tại

    quiz_files = glob.glob(os.path.join(root_dir, '*.html'))
    
    # Loại trừ các tệp không phải bài trắc nghiệm
    valid_quizzes = []
    for f in quiz_files:
        basename = os.path.basename(f)
        # Bỏ qua các tệp không phải là bài kiểm tra được tạo ra
        if basename.startswith('creator_') or basename.startswith('quiz_page_') or basename == 'index.html':
            continue
        # Kiểm tra xem có tệp json tương ứng không
        if os.path.exists(os.path.join(root_dir, basename.replace('.html', '.json'))):
            valid_quizzes.append(basename)

    links = []
    for filename in sorted(valid_quizzes):
        pretty_name = filename.replace('_', ' ').replace('.html', ' ').title()
        links.append({'url': f'/{filename}', 'name': pretty_name, 'filename': filename})
        
    return render_template('creator_page.html', quizzes=links)

@app.route('/create', methods=['POST'])
def create_quiz():
    """Nhận dữ liệu từ form, xử lý và tạo các tệp."""
    quiz_title = request.form.get('quiz_name')
    md_content = request.form.get('md_content')

    if not quiz_title or not md_content:
        return "Lỗi: Vui lòng cung cấp cả tên và nội dung bài trắc nghiệm.", 400

    extracted_data = parse_quiz_from_content(md_content)
    if not extracted_data:
        return "Lỗi: Không trích xuất được câu hỏi nào từ nội dung bạn cung cấp. Vui lòng kiểm tra lại định dạng.", 400

    base_filename = sanitize_filename(quiz_title)
    json_filename = f"{base_filename}.json"
    html_filename = f"{base_filename}.html"

    # Xác định thư mục gốc để lưu file
    if getattr(sys, 'frozen', False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(root_dir, json_filename), 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    # Đọc template và tạo nội dung HTML
    with open(os.path.join(app.root_path, 'templates', 'quiz_page_template.html'), 'r', encoding='utf-8') as f:
        template_content = f.read()

    html_content = template_content.format(QUIZ_TITLE=quiz_title, JSON_FILENAME=json_filename)

    with open(os.path.join(root_dir, html_filename), 'w', encoding='utf-8') as f:
        f.write(html_content)

    return redirect(url_for('index'))

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_quiz(filename):
    """Xóa tệp .html và .json của một bài trắc nghiệm."""
    if getattr(sys, 'frozen', False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.getcwd()

    html_path = os.path.join(root_dir, filename)
    json_path = os.path.join(root_dir, filename.replace('.html', '.json'))

    try:
        if os.path.exists(html_path): os.remove(html_path)
        if os.path.exists(json_path): os.remove(json_path)
    except OSError as e:
        print(f"Lỗi khi xóa tệp: {e}")
        return "Đã xảy ra lỗi khi xóa bài kiểm tra.", 500

    return redirect(url_for('index'))

@app.route('/<path:filename>')
def serve_quiz_page(filename):
    """Phục vụ các tệp HTML và JSON được tạo ra."""
    if getattr(sys, 'frozen', False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
    return send_from_directory(root_dir, filename)


# --- PHẦN 4: CHẠY ỨNG DỤNG ---
if __name__ == '__main__':
    print("Máy chủ đang chạy tại: http://127.0.0.1:5000")
    print("Mở trình duyệt và truy cập địa chỉ trên để sử dụng.")
    app.run(debug=True, port=5000)
