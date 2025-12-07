from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
import re
import json
import os
import string
import glob
import sys


# --- PHẦN 1: KHỞI TẠO ỨNG DỤNG FLASK ---
app = Flask(__name__)

# Tạo thư mục 'data' nếu chưa tồn tại
if not os.path.exists('data'):
    os.makedirs('data')

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
    data_dir = os.path.join(os.getcwd(), 'data')
    quiz_files = glob.glob(os.path.join(data_dir, '*.html'))
    
    quizzes_by_subject = {}

    for f in quiz_files:
        basename = os.path.basename(f)
        if basename.startswith('creator_') or basename.startswith('quiz_page_'):
            continue

        if os.path.exists(os.path.join(data_dir, basename.replace('.html', '.json'))):
            # Quy ước tên tệp: subject_name---quiz_name.html
            parts = basename.replace('.html', '').split('---')
            if len(parts) == 2:
                subject_sanitized, quiz_name_sanitized = parts
                subject_name = subject_sanitized.replace('_', ' ').title()
                quiz_name = quiz_name_sanitized.replace('_', ' ').title()
            else:
                # Xử lý cho các tệp cũ không theo quy ước
                subject_name = "Chưa phân loại"
                quiz_name = basename.replace('.html', '').replace('_', ' ').title()

            if subject_name not in quizzes_by_subject:
                quizzes_by_subject[subject_name] = []
            
            quizzes_by_subject[subject_name].append({
                'url': f'/data/{basename}', 
                'name': quiz_name, 
                'filename': basename
            })
        
    return render_template('creator_page.html', quizzes_by_subject=quizzes_by_subject)

@app.route('/create', methods=['POST'])
def create_quiz():
    """Nhận dữ liệu từ form, xử lý và tạo các tệp."""
    subject_name = request.form.get('subject_name')
    quiz_title = request.form.get('quiz_name')
    md_content = request.form.get('md_content')

    if not all([subject_name, quiz_title, md_content]):
        return "Lỗi: Vui lòng cung cấp đầy đủ tên môn học, tên bài trắc nghiệm và nội dung.", 400

    extracted_data = parse_quiz_from_content(md_content)
    if not extracted_data:
        return "Lỗi: Không trích xuất được câu hỏi nào từ nội dung bạn cung cấp. Vui lòng kiểm tra lại định dạng.", 400

    # Quy ước tên tệp mới: subject---quiz.html
    base_filename = f"{sanitize_filename(subject_name)}---{sanitize_filename(quiz_title)}"
    json_filename = f"{base_filename}.json"
    html_filename = f"{base_filename}.html"

    data_dir = os.path.join(os.getcwd(), 'data')
    with open(os.path.join(data_dir, json_filename), 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    with open(os.path.join(app.root_path, 'templates', 'quiz_page_template.html'), 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Quay lại sử dụng string.Template hoặc str.format vì HTML sẽ không chứa dữ liệu nữa
    # mà sẽ fetch từ file JSON.
    html_content = template_content.replace(
        '{{ QUIZ_TITLE }}', quiz_title
    ).replace(
        '{{ JSON_FILENAME }}', json_filename
    )

    with open(os.path.join(data_dir, html_filename), 'w', encoding='utf-8') as f:
        f.write(html_content)

    return redirect(url_for('index'))

@app.route('/suggest-update', methods=['POST'])
def suggest_update():
    """Nhận góp ý và cập nhật trực tiếp vào tệp JSON của bài trắc nghiệm."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Dữ liệu không hợp lệ"}), 400

    quiz_filename = data.get('quiz_filename')
    question_id = data.get('question_id') # Đây là kiểu int
    new_answer = data.get('new_answer')
    new_explanation = data.get('new_explanation')

    if not all([quiz_filename, question_id, new_answer, new_explanation]):
        return jsonify({"success": False, "message": "Thiếu thông tin cần thiết"}), 400

    # Tệp JSON giờ nằm trong thư mục 'data'
    data_dir = os.path.join(os.getcwd(), 'data')
    json_path = os.path.join(data_dir, quiz_filename)
    
    if not os.path.exists(json_path):
        return jsonify({"success": False, "message": f"Không tìm thấy tệp {quiz_filename}"}), 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            quiz_data = json.load(f)

        question_found = False
        for question in quiz_data:
            if question.get('id') == question_id:
                question['answer'] = new_answer
                question['explanation'] = new_explanation
                question_found = True
                break
        
        if not question_found:
            return jsonify({"success": False, "message": f"Không tìm thấy câu hỏi với ID {question_id}"}), 404

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(quiz_data, f, ensure_ascii=False, indent=4)

        return jsonify({"success": True, "message": "Cập nhật câu hỏi thành công!"})

    except Exception as e:
        print(f"Lỗi khi cập nhật tệp JSON: {e}")
        return jsonify({"success": False, "message": "Đã xảy ra lỗi phía máy chủ."}), 500

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_quiz(filename):
    """Xóa tệp .html và .json của một bài trắc nghiệm."""
    data_dir = os.path.join(os.getcwd(), 'data')
    html_path = os.path.join(data_dir, filename)
    json_path = os.path.join(data_dir, filename.replace('.html', '.json'))
    
    try:
        if os.path.exists(html_path): os.remove(html_path)
        if os.path.exists(json_path): os.remove(json_path)
    except OSError as e:
        print(f"Lỗi khi xóa tệp: {e}")
        return "Đã xảy ra lỗi khi xóa bài kiểm tra.", 500

    return redirect(url_for('index'))

@app.route('/data/<path:filename>')
def serve_quiz_page(filename):
    """Phục vụ các tệp HTML và JSON được tạo ra."""
    data_dir = os.path.join(os.getcwd(), 'data')
    return send_from_directory(data_dir, filename)


# --- PHẦN 4: CHẠY ỨNG DỤNG ---
if __name__ == '__main__':
    print("Máy chủ đang chạy tại: http://127.0.0.1:5000")
    print("Mở trình duyệt và truy cập địa chỉ trên để sử dụng.")
    app.run(debug=True, port=5000)
