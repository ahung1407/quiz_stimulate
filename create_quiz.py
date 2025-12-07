import re
import json
import os
import argparse
import string

# --- PHẦN 1: TEMPLATE HTML ---
# Đây là toàn bộ mã nguồn của một trang web trắc nghiệm.
# Các placeholder {{QUIZ_TITLE}} và {{JSON_FILENAME}} sẽ được thay thế bằng tên bài trắc nghiệm của bạn.
HTML_TEMPLATE = string.Template("""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${QUIZ_TITLE}</title>
    <style>
        :root {
            --primary-color: #007bff; --secondary-color: #f8f9fa; --correct-color: #28a745;
            --incorrect-color: #dc3545; --text-color: #212529; --border-color: #dee2e6;
            --shadow-color: rgba(0, 0, 0, 0.1);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--secondary-color); color: var(--text-color); display: flex;
            justify-content: center; align-items: center; min-height: 100vh; margin: 0;
            padding: 20px; box-sizing: border-box;
        }
        .quiz-container {
            background-color: white; border-radius: 15px; box-shadow: 0 4px 15px var(--shadow-color);
            width: 100%; max-width: 800px; overflow: hidden;
        }
        .quiz-header {
            padding: 20px 30px; background-color: var(--primary-color); color: white;
            display: flex; justify-content: space-between; align-items: center;
        }
        .quiz-header h2 { margin: 0; font-size: 1.5em; }
        #progress { font-size: 1em; font-weight: 500; }
        .quiz-body { padding: 30px; }
        #question-text { font-size: 1.2em; font-weight: 600; margin-bottom: 25px; line-height: 1.5; }
        .options-container { display: flex; flex-direction: column; gap: 15px; }
        .option {
            background-color: #fff; border: 2px solid var(--border-color); border-radius: 10px;
            padding: 15px; cursor: pointer; transition: all 0.2s ease-in-out;
            display: flex; align-items: center;
        }
        .option:hover { border-color: var(--primary-color); }
        .option.selected { border-color: var(--primary-color); background-color: #e7f3ff; }
        .option.correct { background-color: #e9f7ec; border-color: var(--correct-color); color: var(--correct-color); font-weight: bold; }
        .option.incorrect { background-color: #fdecea; border-color: var(--incorrect-color); color: var(--incorrect-color); font-weight: bold; }
        .option-key {
            font-weight: bold; margin-right: 15px; min-width: 20px; height: 20px;
            display: inline-flex; justify-content: center; align-items: center;
        }
        .quiz-footer { padding: 20px 30px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; }
        .btn {
            padding: 12px 25px; border: none; border-radius: 8px; font-size: 1em;
            font-weight: bold; cursor: pointer; color: white; transition: background-color 0.2s;
        }
        #confirm-btn { background-color: var(--primary-color); }
        #confirm-btn:hover { background-color: #0056b3; }
        #confirm-btn:disabled { background-color: #a0a0a0; cursor: not-allowed; }
        #next-btn { background-color: var(--correct-color); }
        #next-btn:hover { background-color: #218838; }
        #explanation-container {
            margin-top: 25px; padding: 20px; background-color: #f1f3f5;
            border-radius: 10px; border-left: 5px solid var(--primary-color); line-height: 1.6;
        }
        #explanation-container strong { color: var(--primary-color); }
        .results-container { padding: 40px; text-align: center; }
        .results-container h2 { font-size: 2em; margin-bottom: 20px; }
        .results-container p { font-size: 1.5em; margin-bottom: 30px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="quiz-container" id="quiz-container">
        <div class="quiz-header">
            <h2 id="quiz-title">${QUIZ_TITLE}</h2>
            <div id="progress"></div>
        </div>
        <div class="quiz-body">
            <p id="question-text">Đang tải câu hỏi...</p>
            <div class="options-container" id="options-container"></div>
            <div id="explanation-container" class="hidden"></div>
        </div>
        <div class="quiz-footer">
            <button class="btn" id="confirm-btn" disabled>Xác nhận</button>
            <button class="btn hidden" id="next-btn">Câu tiếp theo</button>
        </div>
    </div>
    <div class="quiz-container hidden" id="results-container">
        <div class="results-container">
            <h2>Hoàn thành!</h2>
            <p id="score-text"></p>
            <button class="btn" id="restart-btn" style="background-color: var(--primary-color);">Làm lại</button>
        </div>
    </div>
    <script>
        const quizContainer = document.getElementById('quiz-container');
        const resultsContainer = document.getElementById('results-container');
        const questionText = document.getElementById('question-text');
        const optionsContainer = document.getElementById('options-container');
        const explanationContainer = document.getElementById('explanation-container');
        const confirmBtn = document.getElementById('confirm-btn');
        const nextBtn = document.getElementById('next-btn');
        const restartBtn = document.getElementById('restart-btn');
        const progressText = document.getElementById('progress');
        const scoreText = document.getElementById('score-text');
        let quizData = [];
        let currentQuestionIndex = 0;
        let score = 0;
        let selectedAnswer = null;
        let answered = false;
        async function loadQuiz() {
            try {
                const res = await fetch('${JSON_FILENAME}');
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                quizData = await res.json();
                startQuiz();
            } catch (error) {
                console.error("Lỗi khi tải quiz:", error);
                questionText.innerHTML = `<strong>Lỗi tải dữ liệu!</strong><br>Không thể tải tệp <code>${JSON_FILENAME}</code>. Hãy đảm bảo bạn đang chạy trang web này thông qua một máy chủ cục bộ.`;
            }
        }
        function startQuiz() {
            // Xáo trộn câu hỏi mỗi khi bắt đầu
            quizData.sort(() => Math.random() - 0.5);
            currentQuestionIndex = 0;
            score = 0;
            answered = false;
            quizContainer.classList.remove('hidden');
            resultsContainer.classList.add('hidden');
            displayQuestion();
        }
        function displayQuestion() {
            resetState();
            const question = quizData[currentQuestionIndex];
            progressText.textContent = `Câu ${currentQuestionIndex + 1} / ${quizData.length}`;
            questionText.textContent = question.question;
            const sortedOptions = Object.keys(question.options).sort();
            for (const key of sortedOptions) {
                const optionElement = document.createElement('div');
                optionElement.classList.add('option');
                optionElement.dataset.key = key;
                optionElement.innerHTML = `<span class="option-key">${key}</span><span>${question.options[key]}</span>`;
                optionElement.addEventListener('click', () => {
                    if (!answered) {
                        const currentSelected = document.querySelector('.option.selected');
                        if (currentSelected) currentSelected.classList.remove('selected');
                        optionElement.classList.add('selected');
                        selectedAnswer = key;
                        confirmBtn.disabled = false;
                    }
                });
                optionsContainer.appendChild(optionElement);
            }
        }
        function resetState() {
            optionsContainer.innerHTML = '';
            explanationContainer.innerHTML = '';
            explanationContainer.classList.add('hidden');
            confirmBtn.classList.remove('hidden');
            confirmBtn.disabled = true;
            nextBtn.classList.add('hidden');
            nextBtn.textContent = 'Câu tiếp theo';
            selectedAnswer = null;
            answered = false;
        }
        function checkAnswer() {
            answered = true;
            confirmBtn.classList.add('hidden');
            nextBtn.classList.remove('hidden');
            const question = quizData[currentQuestionIndex];
            const isCorrect = selectedAnswer === question.answer;
            if (isCorrect) score++;
            explanationContainer.innerHTML = `<strong>Đáp án đúng: ${question.answer}</strong><br>${question.explanation}`;
            explanationContainer.classList.remove('hidden');
            Array.from(optionsContainer.children).forEach(option => {
                const optionKey = option.dataset.key;
                if (optionKey === question.answer) option.classList.add('correct');
                else if (optionKey === selectedAnswer && !isCorrect) option.classList.add('incorrect');
            });
            if (currentQuestionIndex === quizData.length - 1) {
                nextBtn.textContent = 'Xem kết quả';
            }
        }
        function nextQuestion() {
            currentQuestionIndex++;
            if (currentQuestionIndex < quizData.length) displayQuestion();
            else showResults();
        }
        function showResults() {
            quizContainer.classList.add('hidden');
            resultsContainer.classList.remove('hidden');
            scoreText.textContent = `Bạn đã trả lời đúng ${score} / ${quizData.length} câu!`;
        }
        confirmBtn.addEventListener('click', checkAnswer);
        nextBtn.addEventListener('click', nextQuestion);
        restartBtn.addEventListener('click', startQuiz);
        window.onload = loadQuiz;
    </script>
</body>
</html>
""")

# --- PHẦN 2: HÀM PHÂN TÍCH MARKDOWN ---
# Hàm này được sao chép từ parser.py, không thay đổi.
def parse_quiz_md(file_path: str) -> list:
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy tệp tại đường dẫn '{file_path}'")
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'(\n\s*\*\*\d+\.\s*)', content)
    full_blocks = [blocks[i] + blocks[i+1] for i in range(1, len(blocks)-1, 2)]
    if blocks[0].strip().startswith('**'):
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

# --- PHẦN 3: HÀM CHÍNH ĐỂ TẠO BÀI KIỂM TRA ---
def main():
    # Thiết lập trình phân tích đối số dòng lệnh
    parser = argparse.ArgumentParser(description="Tạo một bài trắc nghiệm HTML từ tệp Markdown.")
    parser.add_argument("input_file", help="Đường dẫn đến tệp .md nguồn.")
    parser.add_argument("quiz_name", help="Tên cho bài trắc nghiệm (ví dụ: 'Bài ôn tập chương 1').")
    args = parser.parse_args()

    input_md_path = args.input_file
    quiz_title = args.quiz_name

    # 1. Chuẩn hóa tên tệp
    # "Bài ôn tập chương 1" -> "bai_on_tap_chuong_1"
    sanitized_name = quiz_title.lower()
    sanitized_name = re.sub(r'\s+', '_', sanitized_name)
    # Loại bỏ các ký tự không hợp lệ cho tên tệp
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    sanitized_name = ''.join(c for c in sanitized_name if c in valid_chars)
    
    if not sanitized_name:
        print("Lỗi: Tên bài trắc nghiệm không hợp lệ.")
        return

    # 2. Phân tích tệp Markdown để lấy dữ liệu
    print(f"Đang phân tích tệp: {input_md_path}...")
    extracted_data = parse_quiz_md(input_md_path)
    if not extracted_data:
        print("Không trích xuất được câu hỏi nào. Vui lòng kiểm tra lại định dạng tệp.")
        return
    print(f"Trích xuất thành công {len(extracted_data)} câu hỏi.")

    # 3. Lưu dữ liệu vào tệp JSON
    json_filename = f"{sanitized_name}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)
    print(f"Đã lưu dữ liệu vào tệp: {json_filename}")

    # 4. Tạo nội dung HTML từ template
    html_content = HTML_TEMPLATE.substitute(
        QUIZ_TITLE=quiz_title,
        JSON_FILENAME=json_filename
    )

    # 5. Lưu nội dung vào tệp HTML
    html_filename = f"{sanitized_name}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Đã tạo thành công bài trắc nghiệm: {html_filename}")
    print("\nBây giờ bạn có thể chạy máy chủ cục bộ và mở tệp .html trong trình duyệt để làm bài!")

if __name__ == '__main__':
    main()
