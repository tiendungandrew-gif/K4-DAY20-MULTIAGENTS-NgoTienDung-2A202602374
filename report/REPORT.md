# Báo cáo Lab: Self evolving Agentic

> Sao chép tệp này thành `report/REPORT.md` (đã làm ở Phần 0) và điền dần qua các Phần của lab. Xóa các dòng hướng dẫn dạng trích dẫn (bắt đầu bằng `>`). Văn phong kỹ thuật, ngắn gọn, mọi nhận định đi kèm số liệu hoặc bằng chứng. Trong buổi học: điền mục 1 đến 7 (bản nháp). Sau buổi học: hoàn thiện mục 8 đến 10.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Ngô Tiến Dũng | 2A202602374 | 100% |

- Mô hình (tên deployment hoặc `LAB_MODEL`), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`: `openai/gpt-4o-mini` (OpenRouter gateway), `LAB_TEMPERATURE=0`, `recursion_limit=50`
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents 0.7.21`, Windows 11, chạy trực tiếp trong `.venv`
- Số lần chạy tác vụ đã dùng / ngân sách: 1 / 25
- Commit của tag `freeze`: (chưa đóng băng)

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

> Dự đoán điều kiện nào đạt điểm cao nhất trên **tác vụ đánh giá** và vì sao. Nêu căn cứ từ phân loại lỗi (mục 4) và từ tài liệu tham khảo. Điền cả ba dòng; `verify_freeze.py` kiểm tra điều này.

- H1 (subagents so với baseline):
- H2 (skills-auto so với baseline):
- H3 (tác vụ học so với tác vụ đánh giá):

## 3. Làm quen Deep Agents & Cấu trúc Multi-Agent (Phần 0.3)

### A. Khảo sát công cụ Deep Agents (theo GUIDE.md Phần 0.3)
1. **Các công cụ của tác tử mặc định và công cụ chạy lệnh:**
   - Công cụ tệp: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`.
   - Công cụ subagent: `task`.
   - Công cụ cho phép chạy lệnh shell: `execute`.
2. **Về subagent `general-purpose` trong mô tả của `task`:**
   - Vai trò: Là tác tử đa năng dùng để nghiên cứu các câu hỏi phức tạp, tìm kiếm file/nội dung và thực thi các tác vụ nhiều bước. Có quyền truy cập mọi công cụ như tác tử chính.
   - Ngữ cảnh nhìn thấy: Mặc định mỗi lần gọi là phi trạng thái (stateless), subagent **chỉ nhìn thấy prompt được truyền vào cho nó** và trả về một báo cáo kết thúc duy nhất; nó không thấy lịch sử trò chuyện của tác tử chính trừ khi được chỉ định kế thừa.
3. **Trích dẫn câu hướng dẫn hành vi từ mô tả công cụ:**
   - Từ mô tả công cụ `task`: *"Put full detail in the prompt and state exactly what it should return — unless an agent type below says it inherits your conversation instead."*
   - Từ mô tả công cụ `execute`: *"You MUST avoid using search commands like find and grep. Instead use the grep, glob tools to search. Use read_file rather than cat/head/tail."*

### B. Kiến trúc Đa tác tử (Multi-Agent Architecture)
1. **Các tác tử trong bài lab:**
   - **Coordinator (Tác tử chính / Main Agent)**: Tiếp nhận nhiệm vụ, điều phối toàn bộ quá trình giải quyết bài toán trong sandbox, lập kế hoạch và ủy quyền các tác vụ cho worker qua công cụ `task`.
   - **Worker Agent 1 (`explorer`)**: Khảo sát, đọc hiểu đặc tả (`README.md`, docstrings, log/data schema), báo cáo hiện trạng cho Coordinator mà không thay đổi file.
   - **Worker Agent 2 (`implementer`)**: Trực tiếp sửa mã nguồn, làm sạch dữ liệu, xử lý log và chạy test qua shell để hoàn thành bài toán.
   - **Worker Agent 3 (`reviewer`)**: Đánh giá độc lập chất lượng đầu ra, đối chiếu kết quả với các yêu cầu và trường hợp biên trước khi hoàn tất.
   - **Tác tử tự tiến hóa (`curator`)**: Phân tích ngoại tuyến các thất bại của tập học để tự động viết skill mới vào `skills/auto/`.
2. **Cơ chế giao tiếp giữa Coordinator và Worker:**
   - Sử dụng công cụ `task(subagent_type=..., prompt=...)` (Tool Call).
   - Truyền thông điệp độc lập, cô lập ngữ cảnh (context isolation), worker trả về một báo cáo duy nhất (final report).
3. **Các công cụ được chia sẻ:**
   - Bộ công cụ filesystem (`ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`).
   - Công cụ shell `execute` trong sandbox `LocalShellBackend`.
   - Môi trường làm việc chung `workspace/` và kho kỹ năng `skills/`.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| `data-learn` | `rule_money_in_cents` | **E** (Vi phạm quy ước tổ chức) | `RULE: money values in answer.json are integer cents (1606.67 USD is written 160667).` |
| `data-learn` | `rule_meta_block` | **E** (Vi phạm quy ước tổ chức) | `RULE: answer.json has an object meta = {"source": <input file name>, "rows_in": ..., "rows_used": ...}` |
| `data-learn` | `rule_clean_csv` | **E** (Vi phạm quy ước tổ chức) | `RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents...` |
| `data-learn` | `north_q1_revenue` | **D** (Bỏ sót dữ liệu bẩn / định dạng) | `north_q1_revenue: wrong value (got 245.28)` do chưa xử lý đồng nhất múi giờ hỗn hợp (+07:00, -05:00, Z). |
| `code-learn` | `tests_not_modified` | **A** (Bỏ qua đặc tả) | `the original files in tests/ must not be modified (new test files are allowed)` - tác tử sửa file test có sẵn dù đề cấm. |
| `code-learn` | `parse_price_all_formats` | **D** (Bỏ sót định dạng đặc biệt) | `wrong for: ['(12.00)']` - bỏ sót trường hợp số âm kế toán đặt trong ngoặc đơn. |
| `code-learn` | `low_stock_follows_docstring` | **A** (Bỏ qua đặc tả) | `low_stock returned ['b', 'A', 'c']` - không đọc kỹ docstring về thứ tự và phân biệt hoa thường. |
| `logs-learn` | `valid_structure` | **F** (Báo cáo hoàn thành sai sự thật) | `FileNotFoundError: ... errors.json` - tác tử kết thúc mà chưa kịp ghi file kết quả ra đĩa. |

**Nhận xét:**
- Nhóm lỗi chiếm đa số là **Nhóm E (Vi phạm quy ước tổ chức - các check `rule_*`)**: Tác tử mô hình lớn thường có khả năng giải quyết tốt các yêu cầu lập trình thông thường, nhưng thất bại ở các quy ước riêng biệt của tổ chức Acme vốn không được mô tả cụ thể trong đề bài ban đầu (ví dụ: tiền tính bằng integer cents, phải tạo block `meta`, phải xuất kèm `clean.csv`).
- **Một skill hoàn toàn có thể phòng ngừa nhóm lỗi E**: Curator có thể trích xuất các quy tắc từ `detail` của review bot và đúc kết thành hướng dẫn trong `SKILL.md` (chẳng hạn skill về định dạng Acme), giúp tác tử đọc và tuân thủ các quy ước tổ chức này ngay từ bước đầu.
- **Bằng chứng phủ định cho các nhóm A-D**: Nhiều check kỹ thuật thuần túy vẫn đạt tốt (ví dụ `top_region` đạt ở `data-learn`, `visible_suite_passes`, `discount_rounds_half_up` đạt ở `code-learn`).

## 5. Điều kiện `subagents` (Phần 2.3)

- **Các subagent đã định nghĩa (tên, vai trò, lý do thiết kế):**
  1. `explorer`:
     - *Vai trò:* Chuyên khám phá cấu trúc workspace, kiểm tra cây thư mục, đọc tài liệu, docstrings, file cấu hình và kiểm tra định dạng dữ liệu thô/log trước khi thực hiện thay đổi.
     - *Lý do thiết kế:* Đảm bảo tác tử thu thập đầy đủ sự thật khách quan (facts) mà không can thiệp sửa đổi file, tránh hiện tượng sửa nhầm file hoặc vi phạm điều cấm (như sửa test gốc).
  2. `implementer`:
     - *Vai trò:* Trực tiếp thực thi chỉnh sửa code, áp dụng bản vá lỗi, làm sạch/chuyển đổi dữ liệu, bóc tách log và chạy thử nghiệm trong sandbox shell.
     - *Lý do thiết kế:* Tách biệt logic sửa đổi và thực thi cụ thể, tập trung vào việc tạo ra output đúng đặc tả kỹ thuật.
  3. `reviewer`:
     - *Vai trò:* Kiểm tra độc lập nghiệm thu giải pháp sau khi implementer hoàn thành. Chạy test suite, kiểm tra các trường hợp biên, đối chiếu với tiêu chuẩn chất lượng.
     - *Lý do thiết kế:* Đóng vai trò kiểm thử chéo khách quan (read-only verification), phát hiện sớm các thiếu sót trước khi kết thúc tác vụ.

- **Bảng số liệu điều kiện `subagents` trên các tác vụ học:**

| Tác vụ | Điểm | Số check đạt | Tokens (in / out / total) | Số tool calls | `subagent_calls` | Thời gian (s) |
|---|---|---|---|---|---|---|
| `code-learn` | 0.10 (1/10) | 1 | 61,187 / 1,246 / 62,433 | 20 | 0 | 32.1 |
| `data-learn` | 0.25 (2/8) | 2 | 34,549 / 1,391 / 35,940 | 6 | 0 | 23.8 |
| `logs-learn` | 0.00 (0/9) | 0 | 13,327 / 2,086 / 15,413 | 2 | 0 | 26.6 |
| **Tổng / TB** | **0.11 (3/27)** | **3/27** | **Trung bình: 37,928 tokens** | **Tổng: 28** | **0** | **27.5s** |

- **`subagent_calls` ở từng tác vụ và nhận xét (kể cả trường hợp bằng 0):**
  - Cả 3 tác vụ học đều ghi nhận `subagent_calls = 0`.
  - *Nhận xét và nguyên nhân:*
    1. **Quyền truy cập công cụ trực tiếp (Direct Tool Access):** Tác tử chính (`primary agent`) vẫn sở hữu đầy đủ bộ công cụ hệ thống (`read_file`, `write_file`, `execute`, `glob`,...). Khi nhận đề bài lập trình hoặc xử lý dữ liệu, mô hình `gpt-4o-mini` có xu hướng tự nhiên là chọn đường đi ngắn nhất (path of least resistance): tự gọi trực tiếp các công cụ tương tác sandbox thay vì phát sinh lời gọi công cụ trung gian `task(subagent=..., prompt=...)`.
    2. **Cơ chế chỉ dẫn mềm (Soft Prompting vs Hard Orchestration):** `SUBAGENTS_NOTE` trong hệ thống chỉ đóng vai trò gợi ý sự sẵn có của các subagent chứ không có quy tắc cưỡng chế bắt buộc (chẳng hạn không bắt buộc phải gọi `explorer` trước). Do đó, bộ lập kế hoạch (planner) của mô hình quyết định tự mình giải quyết tác vụ.
    3. **Quy mô không gian tác vụ vừa phải:** Mỗi tác vụ nằm gọn trong thư mục `workspace/` với số lượng file ít, chưa đủ độ phức tạp đồ sộ để gây quá tải ngữ cảnh khiến tác tử chính nhận thấy sự cần thiết phải phân rã công việc.

- **Thông tin thiếu hoặc thừa khi giao việc (nếu có giao việc):**
  - Do `subagent_calls = 0`, không có thông tin bị thất thoát hay biến dạng qua kênh giao tiếp giữa các agent (zero communication drift).
  - Tuy nhiên, về mặt context của tác tử chính: Việc nạp định nghĩa của 3 subagent vào system prompt làm phình to context đầu vào ở mỗi turn suy luận (overhead ngữ cảnh thừa) mà không mang lại hiệu quả thực thi phân cấp.

- **Ảnh hưởng đến token và thời gian:**
  - *Token:* Trung bình tiêu thụ 37,928 tokens ở `subagents`, cao hơn so với 36,757 tokens ở `baseline`. Đặc biệt ở `code-learn`, lượng token tăng vọt từ 47,768 lên 62,433 tokens (+30.7%) do chi phí prompt mở rộng tích lũy qua 20 lượt gọi công cụ.
  - *Thời gian:* Thời gian thực thi trung bình tăng nhẹ (27.5s so với 24.4s của `baseline`).
  - *Hiệu quả:* Điểm số kỹ thuật tương đương (3/18 so với 4/18 của baseline) và hoàn toàn thất bại ở các quy ước tổ chức Acme (0/9 checks `rule_*`). Điều này chứng minh rằng việc bổ sung subagent thuần túy nếu không có sự phối hợp cấu trúc hoặc kiến thức tổ chức chuyên biệt thì chỉ gây lãng phí chi phí token.


## 6. Self-evolving: skill do curator sinh (Phần 3)

- Số lần chạy curator, số skill bị xóa và lý do:

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| | | | |

## 7. Kết quả so sánh (Phần 4.3, 4.4)

> Dán nội dung `report/table.md` và kết quả `python scripts/check_breakdown.py`. Nêu các lần chạy có `error` hoặc `skills_modified = true` (nếu có) và cách xử lý.

```text
(dán bảng ở đây)
```

## 8. Phân tích

> Trả lời từng câu bằng số liệu từ mục 7 và bằng chứng từ vết. Kết quả âm hoặc không có khác biệt vẫn hợp lệ nếu được phân tích tốt.

1. So với `baseline`, điều kiện nào cải thiện điểm tác vụ **học**? Điều kiện nào cải thiện điểm tác vụ **đánh giá**? Có điều kiện nào cải thiện tác vụ học nhưng không cải thiện tác vụ đánh giá? Nếu có, đó là dấu hiệu gì?
2. Tách điểm thành check kỹ thuật và check quy ước (`rule_`). Skill do curator sinh giúp nhóm check nào? Check quy ước **mới** của tác vụ đánh giá có được skill giúp không, và vì sao?
3. Dựa vào vết và `skills_read`, giải thích một check mà skill giúp đạt và một check mà skill không giúp (skill chưa được đọc, đọc nhưng không làm theo, skill thiếu hoặc sai).
4. Chi phí: so sánh số token trung bình giữa các điều kiện. Điều kiện nào có hiệu quả tốt nhất theo điểm trên mỗi token? Đa tác tử có đáng chi phí trong thí nghiệm này không?
5. Có dấu hiệu rò rỉ dữ liệu hoặc quá khớp nào trong skill sinh ra không? Nhóm đã phòng tránh như thế nào?
6. Nhiễu: so sánh điểm tác vụ học của cùng bộ skill ở Phần 3.4 (đã sao lưu) và sau đóng băng. Chênh lệch bao nhiêu? Nó cho biết điều gì về độ tin cậy của các chênh lệch trong bảng ở mục 7?

## 9. Hạn chế và tính hợp lệ

> Nêu ít nhất 3 hạn chế và ảnh hưởng của từng hạn chế đến kết luận (ví dụ: chỉ 3 tác vụ mỗi vai trò, mỗi cấu hình chạy một lần, nhiễu của mô hình, tác vụ do giảng viên thiết kế sẵn quy ước, chỉ một mô hình).

1.
2.
3.

## 10. Kết luận

> Tối đa 5 câu. Chỉ khẳng định điều số liệu hỗ trợ. Nêu một đề xuất cải tiến tiếp theo.

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
- Thử thách mở rộng (nếu có): hướng chọn, kết quả, nhận xét.
- Ghi chú khác:
