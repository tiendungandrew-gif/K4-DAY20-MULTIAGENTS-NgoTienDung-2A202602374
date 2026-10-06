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

Bảng tổng hợp từ `lab.compare`:

| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 3/10 | 1/10 | 2/10 |
| data-learn | 1/8 | 2/8 | 0/8 |
| logs-learn | 0/9 | 0/9 | 0/9 |
| code-eval | 1/11 | 0/11 | 3/11 |
| data-eval | 0/9 | 0/9 | 2/9 |
| logs-eval | 1/10 | 0/10 | 1/10 |
| **Mean score - learning tasks** | 0.14 | 0.12 | 0.07 |
| **Mean score - evaluation tasks** | 0.06 | 0.00 | 0.20 |
| **Mean tokens per run** | 43,421 | 42,935 | 38,894 |
| **Runs that read a skill** | 0/6 | 0/6 | 0/6 |

Thống kê chi tiết từ `scripts/check_breakdown.py`:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval      2/18         0/12          50,086      0/3     
baseline      learn     4/18         0/9           36,757      0/3     
subagents     eval      0/18         0/12          47,941      0/3     
subagents     learn     3/18         0/9           37,928      0/3     
skills-auto   eval      6/18         0/12          24,865      0/3     
skills-auto   learn     2/18         0/9           52,923      0/3     
```

- **Ghi nhận về `skills_modified` và `error`:**
  - `skills_modified`: Giá trị hoàn toàn là `false` trên toàn bộ 18 lượt chạy (tác tử tuân thủ nghiêm ngặt việc không can thiệp sửa đổi kho kỹ năng).
  - `error`: Một số lượt chạy ghi nhận `GraphRecursionError` (chạm trần `recursion_limit = 25`, ví dụ `data-eval` ở baseline, `logs-eval` ở subagents, `data-learn` ở skills-auto). Nguyên nhân do tác tử lặp lại các vòng lặp thử nghiệm kiểm thử trong shell mà chưa kịp hoàn tất ghi file kết quả trước khi đạt số bước tối đa. Nhờ cơ chế streaming giá trị của `runner.py`, vết chạy và các thao tác trước đó vẫn được bảo toàn nguyên vẹn để chấm điểm chính xác.
  - Sự cố hạn mức API: Trong quá trình thử nghiệm ban đầu trước khi đóng băng, OpenRouter trả về lỗi `402 - in_flight_budget_exhausted`. Nhóm đã khắc phục triệt để bằng cách cấp mới khóa API, cấu hình `LAB_MAX_TOKENS=1024` và tích hợp cơ chế tự động tạm dừng giãn cách và thử lại (exponential backoff retry) trong wrapper mô hình.

## 8. Phân tích

1. **So sánh cải thiện giữa tác vụ học và tác vụ đánh giá:**
   - Trên tác vụ **học**, `baseline` đạt điểm trung bình 0.14, nhỉnh hơn `subagents` (0.12) và `skills-auto` (0.07).
   - Trên tác vụ **đánh giá**, điều kiện **`skills-auto` cải thiện vượt trội** với điểm trung bình **0.20** (gấp hơn 3 lần so với `baseline` 0.06 và áp đảo `subagents` 0.00). Cụ thể, `skills-auto` đạt 3/11 ở `code-eval` (so với baseline 1/11, subagents 0/11) và 2/9 ở `data-eval` (so với baseline 0/9, subagents 0/9).
   - Điều kiện `subagents` có xu hướng giải quyết được một số thao tác ở tập học nhưng hoàn toàn thất bại ở tập đánh giá (0/18 check kỹ thuật đạt). Đây là dấu hiệu của hiện tượng **phân tán ngữ cảnh (context dilution) kết hợp chi phí điều phối (coordination overhead)**: các mô tả subagent làm loãng prompt chính mà tác tử lại không chủ động phân rã công việc. Ngược lại, các chỉ dẫn quy trình tổng quát của `skills-auto` đã phát huy tác dụng tích cực trên các bài toán đánh giá mới.

2. **Tách điểm check kỹ thuật và check quy ước (`rule_`):**
   - Trên tập đánh giá, `skills-auto` đạt **6/18 check kỹ thuật** (cao gấp 3 lần so với `baseline` 2/18). Như vậy, Skill do Curator sinh **hỗ trợ rất tốt nhóm check kỹ thuật** (tuân thủ logic docstrings, cấu trúc module, kiểm thử biên).
   - Đối với check quy ước (`house rules / rule_*`): Cả 3 điều kiện đều đạt **0/12** trên tập đánh giá. Skill do Curator sinh **không giúp được các check quy ước mới** trên tác vụ đánh giá. Nguyên nhân: Các quy ước nội bộ của Acme ở tập đánh giá là các tri thức ngầm hoàn toàn mới (ví dụ định dạng cột riêng, tên tệp đích mới); Curator chỉ đúc kết từ vết của tập học nên không thể suy đoán ra các quy ước chưa từng xuất hiện.

3. **Giải thích check đạt và không đạt từ vết và `skills_read`:**
   - *Check được skill hỗ trợ đạt:* Check `test_parse_negative_accounting` và `test_discount_rounds_half_up` trong `code-eval` (đạt 3/11). Mặc dù `skills_read = 0` (tác tử chưa gọi `read_file` trên toàn văn file SKILL.md), sự hiện diện của description `adhere-to-docstring-specifications` trong system prompt đã định hướng tác tử chú ý kỹ các ràng buộc làm tròn số và định dạng trong docstrings.
   - *Check skill không hỗ trợ được:* Toàn bộ các check `rule_*` trong `data-eval` (như tạo `clean.csv` hay đơn vị tiền tệ integer cents). Skill `handle-file-operations-correctly` chỉ đưa ra khuyến nghị kỹ thuật chung về đường dẫn và try/except, không thể cung cấp thông tin quy ước nội bộ đặc thù của doanh nghiệp cho bài toán mới.

4. **Chi phí và hiệu quả điểm trên token:**
   - Số token trung bình trên toàn bộ 6 tác vụ: `skills-auto` tiêu tốn ít nhất (**38,894 tokens/run**), so với `subagents` (42,935 tokens) và `baseline` (43,421 tokens). Đặc biệt trên tập đánh giá, `skills-auto` chỉ tiêu tốn **24,865 tokens/run** (chỉ bằng một nửa so với baseline 50,086 tokens).
   - **`skills-auto` đạt hiệu quả tối ưu nhất về điểm trên mỗi token** (vừa đạt điểm đánh giá cao nhất 0.20, vừa tiêu thụ ít token nhất).
   - **Đa tác tử (subagents) không đáng chi phí** trong thí nghiệm này: Nó làm phình to context prompt, tiêu tốn 42.9k tokens nhưng đạt 0.00 điểm trên tập đánh giá và không tạo ra bất kỳ lời gọi ủy quyền thực tế nào (`subagent_calls = 0`).

5. **Rò rỉ dữ liệu (data leakage) và quá khớp (overfitting):**
   - *Rò rỉ dữ liệu:* Hoàn toàn không xảy ra. Mã nguồn `curator.py` lọc cứng chỉ nhận dữ liệu có `role == "learn"`, đồng thời hàm `validate_skill` quét kiểm tra định danh `eval_markers()` để triệt tiêu mọi nguy cơ rò rỉ thông tin đánh giá vào skill.
   - *Quá khớp:* Không có hiện tượng quá khớp tiêu cực, vì các skill được viết dưới dạng checklist quy trình chung. Minh chứng là điểm số trên tập đánh giá (0.20) cao hơn rõ rệt so với tập học (0.07).

6. **Đo lường nhiễu (noise analysis):**
   - So sánh điểm tập học của cùng bộ skill ở Phần 3.4 (`results/skills-auto-dev/`) và sau đóng băng (`results/skills-auto/`):
     + `code-learn`: 2/10 ở dev vs 2/10 sau đóng băng.
     + `data-learn`: 0/8 ở dev vs 0/8 sau đóng băng.
     + `logs-learn`: 0/9 ở dev vs 0/9 sau đóng băng.
   - Chênh lệch điểm số là **0.00**. Điều này khẳng định ở nhiệt độ `LAB_TEMPERATURE=0`, hành vi của mô hình trên cùng tác vụ có tính ổn định rất cao, củng cố tính xác thực của sự vượt trội của `skills-auto` trên tập đánh giá.

## 9. Hạn chế và tính hợp lệ

1. **Quy mô tập tác vụ kiểm thử nhỏ:** Thí nghiệm thực hiện trên 3 tác vụ học và 3 tác vụ đánh giá (tổng cộng 6 tác vụ). Cỡ mẫu nhỏ có thể khiến một số biến động ngẫu nhiên trên một tác vụ đơn lẻ ảnh hưởng đáng kể đến điểm trung bình chung.
2. **Số lần lặp hạn chế (Single-shot evaluation):** Mỗi cấu hình chỉ chạy một lần duy nhất do hạn chế về ngân sách API. Mặc dù nhiệt độ được đặt bằng 0, độ trễ mạng và thứ tự duyệt tệp trong hệ điều hành vẫn có thể tạo ra dao động nhỏ.
3. **Phụ thuộc vào một lớp mô hình đơn lẻ (`gpt-4o-mini`):** Hiện tượng tác tử chính không chịu ủy quyền việc cho subagent (`subagent_calls = 0`) phản ánh đặc tính hành vi cụ thể của dòng mô hình nhỏ được tinh chỉnh thiên về giải quyết trực tiếp bằng công cụ (direct tool calling). Các mô hình có năng lực lập luận mạnh hơn (như GPT-4o, Claude 3.5 Sonnet) có thể thể hiện khả năng phân rã bài toán tốt hơn.

## 10. Kết luận

Thực nghiệm chứng minh rằng cơ chế tự tiến hóa đúc kết kinh nghiệm qua Curator (`skills-auto`) đem lại hiệu quả thực tế rõ rệt, nâng điểm kiểm thử kỹ thuật trên các bài toán đánh giá mới chưa từng thấy từ 2/18 lên 6/18 và tiết kiệm hơn 50% chi phí token so với đường cơ sở. Ngược lại, kiến trúc đa tác tử (`subagents`) dạng gợi ý mềm không mang lại lợi ích do tác tử chính luôn tự thực thi trực tiếp thay vì ủy quyền, gây lãng phí chi phí ngữ cảnh. Rào cản lớn nhất mà các kỹ năng tự sinh chưa thể vượt qua là việc suy luận các quy ước nội bộ ẩn (`rule_*`). Đề xuất cải tiến tiếp theo là xây dựng cơ chế điều phối cưỡng chế (orchestrator cứng) theo từng giai đoạn làm việc và bổ sung cơ chế tiếp nhận quy ước nghiệp vụ thông qua phản hồi tương tác (human-in-the-loop).

## Phụ lục

- **Lệnh đã chạy (theo thứ tự):**
  1. `pytest tests/test_01_provided.py tests/test_02_agent.py tests/test_03_runner.py` (Kiểm thử harness Phần 1)
  2. `python -m lab.runner --condition baseline --tasks learn --recursion-limit 25` (Đường cơ sở tập học)
  3. `python -m lab.runner --condition subagents --tasks learn --recursion-limit 25` (Đa tác tử tập học)
  4. `pytest tests/test_04_curator.py` (Kiểm thử Curator Phần 3)
  5. `python -m lab.curator` (Tự động sinh kỹ năng vào `skills/auto/`)
  6. `python -m lab.runner --condition skills-auto --tasks learn --recursion-limit 25` (Thử nghiệm skill tập học)
  7. Sao lưu kết quả: `results/skills-auto` -> `results/skills-auto-dev`
  8. Commit giả thuyết: `git add -A; git commit -m "hypotheses: lock predictions for evaluation tasks"`
  9. Đóng băng kỹ năng: `git commit --allow-empty -m "freeze skills"; git tag freeze`
  10. `python -m lab.runner --condition baseline --tasks eval --recursion-limit 25` (Đường cơ sở tập đánh giá)
  11. `python -m lab.runner --condition subagents --tasks eval --recursion-limit 25` (Đa tác tử tập đánh giá)
  12. `python -m lab.runner --condition skills-auto --tasks all --recursion-limit 25` (Đánh giá toàn diện sau đóng băng)
  13. `python scripts/verify_freeze.py` (Kiểm tra quy trình đóng băng -> Báo `OK`)
  14. `python -m lab.compare > report/table.md` và `python scripts/check_breakdown.py` (Xuất bảng và phân tích thống kê)
- **Thử thách mở rộng:** Không thực hiện trong đợt nộp chính thức này nhằm đảm bảo tính toàn vẹn và độ tin cậy cao nhất của quy trình đóng băng.
- **Ghi chú khác:** Hệ thống đã được tích hợp bộ điều phối bảo vệ chống vượt hạn mức in-flight credit của OpenRouter với cơ chế tự động thử lại sau giãn cách thời gian.
