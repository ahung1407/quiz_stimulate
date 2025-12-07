import re
import json
import os
 
def parse_quiz_md(file_path: str) -> list:
    """
    Phân tích tệp markdown chứa các câu hỏi trắc nghiệm và trích xuất chúng.
 
    Args:
        file_path: Đường dẫn đến tệp .md.
 
    Returns:
        Một danh sách các dictionary, mỗi dictionary chứa thông tin một câu hỏi.
        Trả về danh sách rỗng nếu không tìm thấy câu hỏi nào.
    """
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy tệp tại đường dẫn '{file_path}'")
        return []
 
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
 
    # Tách toàn bộ nội dung thành các khối câu hỏi, mỗi khối bắt đầu bằng **<số>.
    # re.split sẽ giữ lại phần phân tách nếu nó nằm trong một nhóm bắt giữ (capturing group).
    blocks = re.split(r'(\n\s*\*\*\d+\.\s*)', content)
 
    # Ghép lại các phần đã tách một cách chính xác
    # ['intro', '**1. ', 'question 1 content', '**2. ', 'question 2 content', ...]
    # -> ['intro', '**1. question 1 content', '**2. question 2 content', ...]
    full_blocks = [blocks[i] + blocks[i+1] for i in range(1, len(blocks)-1, 2)]
    # Thêm khối đầu tiên nếu nó không phải là câu hỏi
    if not blocks[0].strip().startswith('**'):
        # Bỏ qua phần giới thiệu ban đầu
        pass
    else: # Trường hợp tệp bắt đầu ngay bằng câu hỏi
        full_blocks.insert(0, blocks[0])
 
    # Regex để phân tích từng khối câu hỏi
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
            
            # Trích xuất các lựa chọn
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
 
def main():
    """
    Hàm chính để chạy kịch bản trích xuất.
    """
    input_file = 'd:\\Minh_Hung\\HTN\\Quiz_stimulate\\quiz.md'
    output_file = 'd:\\Minh_Hung\\HTN\\Quiz_stimulate\\quiz_data.json'
 
    print(f"Đang đọc dữ liệu từ: {input_file}")
 
    extracted_data = parse_quiz_md(input_file)
 
    if not extracted_data:
        print("Không trích xuất được câu hỏi nào. Vui lòng kiểm tra lại định dạng tệp.")
        return
 
    print(f"Trích xuất thành công {len(extracted_data)} câu hỏi.")
 
    # Lưu dữ liệu vào tệp JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)
 
    print(f"Đã lưu dữ liệu vào: {output_file}")
    print("Tệp JSON đã sẵn sàng để bạn import vào giao diện web.")
 
if __name__ == '__main__':
    main()
