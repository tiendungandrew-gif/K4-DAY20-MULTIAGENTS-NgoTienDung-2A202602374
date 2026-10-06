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

- H1 (subagents so với baseline): Điều kiện subagents sẽ không cải thiện đáng kể điểm số trên tác vụ đánh giá so với baseline (chênh lệch điểm dưới 10%), nhưng sẽ tiêu tốn lượng token cao hơn từ 15% đến 30% do chi phí context overhead của các mô tả subagent trong prompt. Đồng thời, tác tử chính vẫn có xu hướng tự thực thi trực tiếp thay vì ủy quyền (subagent_calls xấp xỉ 0). Căn cứ: Xu hướng direct tool usage của các mô hình LLM nhỏ (GPT-4o-mini) trên các không gian tác vụ vừa phải khi không có cơ chế bắt buộc phân rã, và hiện tượng coordination overhead trong kiến trúc đa tác tử.
- H2 (skills-auto so với baseline): Điều kiện skills-auto sẽ cải thiện nhẹ ở một số check kỹ thuật (như tuân thủ docstrings hoặc tránh sửa test có sẵn), nhưng sẽ KHÔNG cải thiện các check quy ước nội bộ mới (các check rule_* trong tập đánh giá). Điểm trung bình tổng thể của skills-auto trên tập đánh giá sẽ chỉ ngang bằng hoặc nhỉnh hơn baseline một biên độ nhỏ. Căn cứ: Nghiên cứu SkillsBench và SkillEvolBench chỉ ra rằng các skill do LLM tự sinh (curated by LLM) khó khái quát hóa ra ngoài phân phối dữ liệu huấn luyện (out-of-distribution transfer gap), và các quy ước nội bộ ẩn của Acme trong tập đánh giá là hoàn toàn mới lạ so với tập học.
- H3 (tác vụ học so với tác vụ đánh giá): Điều kiện skills-auto sẽ đạt hiệu quả trên tác vụ học cao hơn rõ rệt so với tác vụ đánh giá, phản ánh hiện tượng quá khớp ngữ cảnh (in-context overfitting). Các quy tắc được Curator đúc kết từ vết thất bại của tập học chỉ giải quyết trực diện các vấn đề đã thấy (in-distribution), trong khi tác vụ đánh giá có dữ liệu và quy ước mới khiến tri thức đúc kết không chuyển giao đầy đủ. Căn cứ: Phát hiện từ SkillEvolBench về sự suy giảm hiệu quả khi chuyển từ train tasks sang test tasks của các hệ thống tự sinh skill.

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

- **Số lần chạy curator, số skill bị xóa và lý do:**
  - *Số lần chạy curator:* 1 lần (`python -m lab.curator`), đọc các vết chạy từ `results/baseline/` và sinh ra 3 skill hợp lệ.
  - *Số skill bị xóa:* 0 skill. Cả 3 skill sinh ra đều thỏa mãn đầy đủ quy cách an toàn (`validate_skill`), frontmatter YAML hợp lệ, độ dài xúc tích (9 dòng, < 40 dòng khuyến nghị), không chứa định danh đánh giá (`eval_markers`), và các chỉ dẫn có tính thực tiễn cao.

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `avoid-modifying-test-files` | **Tổng quát:** Áp dụng cho mọi bài toán công nghệ phần mềm và bảo trì mã nguồn có sẵn bộ kiểm thử. | **Đúng:** Khuyên không sửa file test có sẵn, tạo test file mới nếu cần mở rộng, kiểm tra test suite chạy đạt sau khi sửa. | 9 dòng (4 dòng YAML, 5 dòng checklist). Description: *"Use this skill when working with test files to ensure that original test files remain unchanged."* Nêu rõ tình huống kích hoạt. `skills_read = 0`. |
| `adhere-to-docstring-specifications` | **Tổng quát:** Áp dụng cho việc lập trình module/hàm tuân thủ hợp đồng giao diện (docstring specs). | **Đúng:** Khuyên đọc kỹ docstring trước khi code, so khớp định dạng output và kiểu dữ liệu, viết test cho edge cases trong docstring. | 9 dòng (4 dòng YAML, 5 dòng checklist). Description: *"Use this skill when implementing functions to ensure they behave as described in their docstrings."* Nêu rõ mục đích áp dụng. `skills_read = 0`. |
| `handle-file-operations-correctly` | **Tổng quát:** Áp dụng cho các bài toán phân tích dữ liệu, bóc tách log và xuất tệp kết quả (I/O). | **Đúng:** Khuyên kiểm tra đường dẫn, xác thực file tồn tại trước khi đọc/ghi, dùng try/except xử lý lỗi, xác thực cấu trúc và định dạng dữ liệu đầu ra trước khi ghi đĩa. | 9 dòng (4 dòng YAML, 5 dòng checklist). Description: *"Use this skill when performing file operations to avoid common errors related to file handling."* Mô tả ngữ cảnh rõ ràng. `skills_read = 0`. |

- **Giải thích việc dùng skill và hiện tượng `skills_read`:**
  - Ở Phần 3.4 trên 3 tác vụ học, kết quả ghi nhận `skills_read = 0` trên cả 3 lần chạy (`code-learn`: score=2/10, 50.7k tokens; `data-learn`: score=0/8, 95.3k tokens; `logs-learn`: score=0/9, 15.6k tokens).
  - *Nguyên nhân:*
    1. Bộ đếm `skills_read` được tính khi tác tử thực hiện lời gọi công cụ `read_file` trên đường dẫn chứa tiền tố `skills/`. Khi nhận chỉ dẫn từ người dùng, tác tử `gpt-4o-mini` tập trung ngay vào không gian bài toán trong `workspace/` (ví dụ `glob`, `read_file("workspace/...")`, `execute(...)`) mà bỏ qua bước chủ động đọc toàn văn file `SKILL.md` qua công cụ `read_file`.
    2. Tuy nhiên, thông tin tóm tắt `description` của skill đã được đưa vào system prompt thông qua tham số `skills=["/skills/"]` của Deep Agents. Nhờ có định hướng này, ở tác vụ `code-learn`, tác tử đã chú ý hơn đến docstrings và vượt qua được 2 check kỹ thuật (`other_caller_fixed`, `low_stock_follows_docstring`), nâng điểm từ 1/10 lên 2/10 so với điều kiện `subagents`.
    3. Ở `data-learn` và `logs-learn`, do tác tử không đọc chi tiết nội dung checklist bên trong `SKILL.md` (chỉ dừng ở nhận biết description), các yêu cầu định dạng output phức tạp và quy ước nội bộ Acme (`rule_*`) vẫn chưa được áp dụng thành công trước khi chạm giới hạn đệ quy (`recursion_limit`).


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
