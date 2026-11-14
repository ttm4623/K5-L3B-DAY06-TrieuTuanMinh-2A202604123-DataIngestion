# Báo cáo cá nhân — Day 6

**Sinh viên:** Trieu Tuan Minh
**MSSV:** 2A202604123
**Trạng thái báo cáo:** Các metric retrieval dưới đây được chép từ output terminal do người dùng cung cấp; trace từng câu và đánh giá thủ công chưa có.

## 1. Mục tiêu

So sánh ba chiến lược retrieval trên cùng corpus và embedding: A dùng chunk kích thước cố định, B dùng chunk theo đoạn, C dùng chunk theo đoạn kết hợp metadata filter. Các chỉ số cần có gồm Hit@1, Evidence Hit@3, coherence, metadata, grounding và tác động tài nguyên.

## 2. Dữ liệu và khả năng tái lập

- **Nguồn:** Project Gutenberg, eBook #39272, *The Inventions, Researches and Writings of Nikola Tesla*, của Thomas Commerford Martin. Manifest ghi nguồn công khai/public domain và URL `https://www.gutenberg.org/cache/epub/39272/pg39272-images.html`.
- **Corpus cục bộ:** `starter/data/pg39272-images.html`.
- **Manifest:** `data/manifest.json` liệt kê 43 đơn vị.
- **Kiểm tra parser:** khi gọi `load_html_corpus` trên corpus hiện có, parser trả về 1 đơn vị với `page_id` rỗng và 967.347 ký tự. Kết quả này không tương ứng với 43 đơn vị trong manifest; do đó chưa thể coi mapping unit/evidence là hợp lệ.
- **Benchmark:** `data/tesla_benchmark.json` có 20 câu, gồm 15 dev và 5 test; cả 20 câu có `evidence_quote`. Không câu nào khai báo trường `filter`, nên benchmark hiện tại không kiểm chứng được câu hỏi/filter metadata.
- **Kết quả ingest theo terminal:** A tạo 2.150 chunks; B và C mỗi chiến lược tạo 1.210 chunks. Tổng 4.570 chunks, khớp tổng số dòng đã quan sát trước đó trong bảng `chunks`.
- **Giới hạn truy vết:** lần kiểm tra parser riêng trước đó chỉ trả về một unit có `page_id` rỗng, không khớp 43 units trong manifest. Output benchmark không có trace top-3 để kiểm tra unit/source của từng hit.

## 3. Cấu hình trong source

| Chiến lược | Cấu hình khai báo |
|---|---|
| A | Fixed-size, `size=500`, `overlap=50` |
| B | Theo đoạn, `max_size=800` |
| C | Cùng chunking với B; áp dụng filter `section="chapters"` cố định |

Terminal xác nhận model `all-MiniLM-L6-v2`, vector dimension 384; source khai báo PostgreSQL + pgvector và cosine distance. C áp dụng filter `section="chapters"` cố định cho mọi câu hỏi, trong khi benchmark không có trường filter; vì vậy chưa thể đánh giá filter theo từng câu hỏi.

## 4. Kết quả

| Chiến lược | Tập | Hit@1 | Hit@3 | Số chunks |
|---|---|---:|---:|---|
| A | Dev (15 câu) | 6.67% (1/15) | 13.33% (2/15) | 2,150 |
| A | Test (5 câu) | 40.00% (2/5) | 40.00% (2/5) | 2,150 |
| B | Dev (15 câu) | 6.67% (1/15) | 13.33% (2/15) | 1,210 |
| B | Test (5 câu) | 20.00% (1/5) | 20.00% (1/5) | 1,210 |
| C | Dev (15 câu) | 6.67% (1/15) | 13.33% (2/15) | 1,210 |
| C | Test (5 câu) | 20.00% (1/5) | 20.00% (1/5) | 1,210 |

### Truy vấn similarity kiểm thử riêng

Output terminal có một truy vấn top-3 riêng, không thuộc bảng benchmark Hit@1/Hit@3. Theo `run_pipeline.py`, câu truy vấn là “What did Tesla invent regarding alternating current motors?”:

| Rank | Chunk ID | Cosine similarity | Preview nội dung (terminal đã cắt ngắn) |
|---:|---|---:|---|
| 1 | `_fixed_020` | 0.7939 | `onstruct alternating current apparatus of fair efficiency ... tests of Prof. Anthony ... when Tesla motors in the hand...` |
| 2 | `_fixed_217` | 0.7654 | `similar systems ... driving-belts, fixed and loose pulleys ... Mr. Tesla believes he is the first to operate electro-...` |
| 3 | `_fixed_019` | 0.7237 | `...motors that have now become known the world over ... the alternating current had no wel...` |

Các ID hiển thị không có page/unit prefix; không dùng ba score này thay cho metric benchmark hay xem chúng là trace của từng câu benchmark.

| Tiêu chí thủ công/tài nguyên | Kết quả hiện có |
|---|---|
| Coherence trên cùng 10 vị trí, thang 0–2 | Chưa chấm |
| Metadata đúng/đủ trên top-3 của test | Chưa kiểm tra |
| Filter compliance | Chưa đo; benchmark không có filter |
| Grounding trên 5 câu test/chiến lược, thang 0–2 | Chưa chấm |
| Số chunks theo chiến lược | A: 2.150; B: 1.210; C: 1.210 |
| Thời gian và chi phí | Không có trong output terminal |
| Chunk ID và similarity theo từng câu benchmark | Chưa có; chỉ có top-3 của truy vấn kiểm thử riêng ở trên |

Metric và top-3 smoke test được chép từ output terminal; chưa có trace theo từng câu benchmark để kiểm tra lại. Nhật ký [`artifacts/experiment_log.csv`](../../artifacts/experiment_log.csv) và bảng text [`starter/results/evaluation_summary.txt`](../../starter/results/evaluation_summary.txt) lưu các số liệu được cung cấp.

## 5. Phân tích

Trên 5 câu test theo output terminal, A đạt Hit@1/Hit@3 40% (2/5), cao hơn B và C một câu (20%, 1/5). Trên 15 câu dev, cả ba bằng nhau (Hit@1 1/15; Hit@3 2/15). Đây chỉ là chênh lệch nhỏ trên test n=5, chưa đủ để khái quát. Tổng số chunks khớp với 4.570 dòng đã quan sát, nhưng vẫn cần trace từng câu để kiểm tra kết quả và truy vết nguồn. Parser riêng trả về một unit ID rỗng, chưa khớp manifest.

Không có câu nào trong benchmark yêu cầu filter. Do đó, dù source C đang áp dụng `section="chapters"`, benchmark hiện tại không thể đo lợi ích của filter hoặc tuân thủ filter theo yêu cầu người dùng.

## 6. Hạn chế và bước tiếp theo

1. Sửa/kiểm chứng parser và mapping unit để số đơn vị, ID nguồn và evidence khớp manifest/benchmark.
2. Bổ sung các câu benchmark có filter hợp lệ, gồm ít nhất một câu test; xác minh evidence trước khi chạy.
3. Chạy A/B/C trên cùng dữ liệu và lưu trace top-3 có chunk ID, nội dung, score, metadata và nhãn gold.
4. Tính metric tự động riêng dev/test; chấm thủ công coherence, metadata và grounding theo mẫu cố định, ghi nhãn cùng lý do.
5. Ghi số chunks, thời gian, chi phí, phiên bản môi trường và log lần chạy để có thể tái lập.

**Kết luận:** Theo output terminal, A có retrieval test cao hơn B/C một câu trong bộ 5 câu; B và C bằng nhau. Kết quả nhỏ này chỉ mang tính quan sát trên benchmark hiện tại. Cần lưu trace top-3 và khắc phục sai lệch parser/manifest trước khi kết luận rộng hơn.
