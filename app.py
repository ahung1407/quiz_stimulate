from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_from_directory
import re
import json
import os
import string
import glob

# --- PHẦN 1: KHỞI TẠO ỨNG DỤNG FLASK ---
app = Flask(__name__)

# --- PHẦN 2: TEMPLATE HTML CHO TRANG CHỦ VÀ TRANG TRẮC NGHIỆM ---
# Template cho trang chủ (nơi bạn tạo bài trắc nghiệm)
CREATOR_PAGE_TEMPLATE = string.Template("""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tạo Bài Trắc Nghiệm Mới</title>
    <style>
        body { font-family: sans-serif; background-color: #f0f2f5; margin: 0; padding: 2rem; }
        .container { max-width: 900px; margin: auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        input[type="text"], textarea {
            width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 4px;
            font-size: 1rem; box-sizing: border-box;
        }
        textarea { min-height: 300px; font-family: monospace; }
        .btn {
            display: inline-block; padding: 0.75rem 1.5rem; background-color: #007bff; color: white;
            border: none; border-radius: 4px; font-size: 1rem; font-weight: bold; cursor: pointer;
            text-decoration: none; text-align: center;
        }
        .btn:hover { background-color: #0056b3; }
        .quiz-list { list-style: none; padding: 0; }
        .quiz-list li { background: #f8f9fa; padding: 1rem; border: 1px solid #dee2e6; border-radius: 4px; margin-bottom: 0.5rem; }
        .quiz-list a { text-decoration: none; color: #007bff; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Công cụ tạo bài trắc nghiệm</h1>
        <form action="/create" method="post">
            <div class="form-group">
                <label for="quiz_name">Tên bài trắc nghiệm:</label>
                <input type="text" id="quiz_name" name="quiz_name" placeholder="Ví dụ: Bài ôn tập chương 1" required>
            </div>
            <div class="form-group">
                <label for="md_content">Dán nội dung Markdown vào đây:</label>
                <textarea id="md_content" name="md_content" required></textarea>
            </div>
            <button type="submit" class="btn">Tạo bài trắc nghiệm</button>
        </form>
        <hr style="margin: 2rem 0;">
        <h2>Các bài trắc nghiệm đã tạo</h2>
        <ul class="quiz-list">
            $quiz_links
        </ul>
    </div>
</body>
</html>
""")

# Template cho các bài trắc nghiệm được tạo ra (tương tự như trước)
QUIZ_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{QUIZ_TITLE}</title><style>:root{{--primary-color:#007bff;--secondary-color:#f8f9fa;--correct-color:#28a745;--incorrect-color:#dc3545;--text-color:#212529;--border-color:#dee2e6;--shadow-color:rgba(0,0,0,.1)}}body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background-color:var(--secondary-color);color:var(--text-color);display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:20px;box-sizing:border-box}}.quiz-container{{background-color:#fff;border-radius:15px;box-shadow:0 4px 15px var(--shadow-color);width:100%;max-width:800px;overflow:hidden}}.quiz-header{{padding:20px 30px;background-color:var(--primary-color);color:#fff;display:flex;justify-content:space-between;align-items:center}}.quiz-header h2{{margin:0;font-size:1.5em}}#progress{{font-size:1em;font-weight:500}}.quiz-body{{padding:30px}}#question-text{{font-size:1.2em;font-weight:600;margin-bottom:25px;line-height:1.5}}.options-container{{display:flex;flex-direction:column;gap:15px}}.option{{background-color:#fff;border:2px solid var(--border-color);border-radius:10px;padding:15px;cursor:pointer;transition:all .2s ease-in-out;display:flex;align-items:center}}.option:hover{{border-color:var(--primary-color)}}.option.selected{{border-color:var(--primary-color);background-color:#e7f3ff}}.option.correct{{background-color:#e9f7ec;border-color:var(--correct-color);color:var(--correct-color);font-weight:700}}.option.incorrect{{background-color:#fdecea;border-color:var(--incorrect-color);color:var(--incorrect-color);font-weight:700}}.option-key{{font-weight:700;margin-right:15px;min-width:20px;height:20px;display:inline-flex;justify-content:center;align-items:center}}.quiz-footer{{padding:20px 30px;border-top:1px solid var(--border-color);display:flex;justify-content:flex-end}}.btn{{padding:12px 25px;border:none;border-radius:8px;font-size:1em;font-weight:700;cursor:pointer;color:#fff;transition:background-color .2s}}#confirm-btn{{background-color:var(--primary-color)}}#confirm-btn:hover{{background-color:#0056b3}}#confirm-btn:disabled{{background-color:#a0a0a0;cursor:not-allowed}}#next-btn{{background-color:var(--correct-color)}}#next-btn:hover{{background-color:#218838}}#explanation-container{{margin-top:25px;padding:20px;background-color:#f1f3f5;border-radius:10px;border-left:5px solid var(--primary-color);line-height:1.6}}#explanation-container strong{{color:var(--primary-color)}}.results-container{{padding:40px;text-align:center}}.results-container h2{{font-size:2em;margin-bottom:20px}}.results-container p{{font-size:1.5em;margin-bottom:30px}}.hidden{{display:none}}</style></head><body><div class=quiz-container id=quiz-container><div class=quiz-header><h2 id=quiz-title>{QUIZ_TITLE}</h2><div id=progress></div></div><div class=quiz-body><p id=question-text>Đang tải câu hỏi...</p><div class=options-container id=options-container></div><div class="hidden"id=explanation-container></div></div><div class=quiz-footer><button class=btn id=confirm-btn disabled>Xác nhận</button><button class="btn hidden"id=next-btn>Câu tiếp theo</button></div></div><div class="quiz-container hidden"id=results-container><div class=results-container><h2>Hoàn thành!</h2><p id=score-text></p><button class=btn id=restart-btn style=background-color:var(--primary-color)>Làm lại</button></div></div><script>const quizContainer=document.getElementById("quiz-container"),resultsContainer=document.getElementById("results-container"),questionText=document.getElementById("question-text"),optionsContainer=document.getElementById("options-container"),explanationContainer=document.getElementById("explanation-container"),confirmBtn=document.getElementById("confirm-btn"),nextBtn=document.getElementById("next-btn"),restartBtn=document.getElementById("restart-btn"),progressText=document.getElementById("progress"),scoreText=document.getElementById("score-text");let quizData=[],currentQuestionIndex=0,score=0,selectedAnswer=null,answered=!1;async function loadQuiz(){{try{{const e=await fetch("{JSON_FILENAME}");if(!e.ok)throw new Error(`HTTP error! status: ${{e.status}}`);quizData=await e.json(),startQuiz()}}catch(e){{console.error("Lỗi khi tải quiz:",e),questionText.innerHTML=`<strong>Lỗi tải dữ liệu!</strong><br>Không thể tải tệp <code>{JSON_FILENAME}</code>. Hãy đảm bảo tệp này tồn tại.`}}}}function startQuiz(){{quizData.sort(()=>Math.random()-.5),currentQuestionIndex=0,score=0,answered=!1,quizContainer.classList.remove("hidden"),resultsContainer.classList.add("hidden"),displayQuestion()}}function displayQuestion(){{resetState();const e=quizData[currentQuestionIndex];progressText.textContent=`Câu ${{currentQuestionIndex+1}} / ${{quizData.length}}`,questionText.textContent=e.question;const t=Object.keys(e.options).sort();for(const n of t){{const t=document.createElement("div");t.classList.add("option"),t.dataset.key=n,t.innerHTML=`<span class="option-key">${{n}}</span><span>${{e.options[n]}}</span>`,t.addEventListener("click",()=>{{answered||(document.querySelector(".option.selected")?.classList.remove("selected"),t.classList.add("selected"),selectedAnswer=n,confirmBtn.disabled=!1)}}),optionsContainer.appendChild(t)}}}}function resetState(){{optionsContainer.innerHTML="",explanationContainer.innerHTML="",explanationContainer.classList.add("hidden"),confirmBtn.classList.remove("hidden"),confirmBtn.disabled=!0,nextBtn.classList.add("hidden"),nextBtn.textContent="Câu tiếp theo",selectedAnswer=null,answered=!1}}function checkAnswer(){{answered=!0,confirmBtn.classList.add("hidden"),nextBtn.classList.remove("hidden");const e=quizData[currentQuestionIndex],t=selectedAnswer===e.answer;t&&score++,explanationContainer.innerHTML=`<strong>Đáp án đúng: ${{e.answer}}</strong><br>${{e.explanation}}`,explanationContainer.classList.remove("hidden"),Array.from(optionsContainer.children).forEach(n=>{{const o=n.dataset.key;o===e.answer?n.classList.add("correct"):o===selectedAnswer&&!t&&n.classList.add("incorrect")}}),currentQuestionIndex===quizData.length-1&&(nextBtn.textContent="Xem kết quả")}}function nextQuestion(){{currentQuestionIndex++,currentQuestionIndex<quizData.length?displayQuestion():showResults()}}function showResults(){{quizContainer.classList.add("hidden"),resultsContainer.classList.remove("hidden"),scoreText.textContent=`Bạn đã trả lời đúng ${{score}} / ${{quizData.length}} câu!`}}confirmBtn.addEventListener("click",checkAnswer),nextBtn.addEventListener("click",nextQuestion),restartBtn.addEventListener("click",startQuiz),window.onload=loadQuiz;</script></body></html>
"""

# --- PHẦN 3: CÁC HÀM TIỆN ÍCH (TÁI SỬ DỤNG TỪ create_quiz.py) ---
def parse_quiz_from_content(content: str) -> list:
    """Phân tích nội dung markdown từ một chuỗi thay vì một tệp."""
    # (Logic giống hệt hàm parse_quiz_md trước đây)
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

# --- PHẦN 4: CÁC ROUTE CỦA MÁY CHỦ WEB ---
@app.route('/')
def index():
    """Hiển thị trang chủ để tạo bài trắc nghiệm và liệt kê các bài đã có."""
    # Tìm tất cả các tệp .html trong thư mục hiện tại
    quiz_files = glob.glob('*.html')
    # Loại trừ các tệp không phải bài trắc nghiệm (nếu có)
    quiz_files = [f for f in quiz_files if os.path.exists(f.replace('.html', '.json'))]
    
    links_html = ''
    for filename in sorted(quiz_files):
        # Lấy tên đẹp từ tên tệp
        pretty_name = filename.replace('_', ' ').replace('.html', ' ').title()
        links_html += f'<li><a href="/{filename}" target="_blank">{pretty_name}</a></li>'
        
    if not links_html:
        links_html = "<li>Chưa có bài trắc nghiệm nào.</li>"
        
    return render_template_string(CREATOR_PAGE_TEMPLATE.safe_substitute(quiz_links=links_html))

@app.route('/create', methods=['POST'])
def create_quiz():
    """Nhận dữ liệu từ form, xử lý và tạo các tệp."""
    quiz_title = request.form.get('quiz_name')
    md_content = request.form.get('md_content')

    if not quiz_title or not md_content:
        return "Lỗi: Vui lòng cung cấp cả tên và nội dung bài trắc nghiệm.", 400

    # 1. Phân tích nội dung markdown
    extracted_data = parse_quiz_from_content(md_content)
    if not extracted_data:
        return "Lỗi: Không trích xuất được câu hỏi nào từ nội dung bạn cung cấp. Vui lòng kiểm tra lại định dạng.", 400

    # 2. Chuẩn hóa tên tệp
    base_filename = sanitize_filename(quiz_title)
    json_filename = f"{base_filename}.json"
    html_filename = f"{base_filename}.html"

    # 3. Lưu tệp JSON
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    # 4. Tạo và lưu tệp HTML
    html_content = QUIZ_PAGE_TEMPLATE.format(
        QUIZ_TITLE=quiz_title,
        JSON_FILENAME=json_filename
    )
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 5. Chuyển hướng người dùng về trang chủ
    return redirect(url_for('index'))

@app.route('/<path:filename>')
def serve_quiz_page(filename):
    """Phục vụ các tệp HTML và JSON được tạo ra."""
    return send_from_directory('.', filename)


# --- PHẦN 5: CHẠY ỨNG DỤNG ---
if __name__ == '__main__':
    print("Máy chủ đang chạy tại: http://127.0.0.1:5000")
    print("Mở trình duyệt và truy cập địa chỉ trên để sử dụng.")
    app.run(debug=True, port=5000)
