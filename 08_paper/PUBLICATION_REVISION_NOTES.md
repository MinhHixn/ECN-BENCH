# Bản khôi phục đầy đủ — 06/09/2026

## Bản nào cần đọc?

`ecn_bench_paper.pdf` là báo cáo kỹ thuật đầy đủ, không còn là bản 10 trang. Nguồn chính là `ecn_bench_paper.tex`, kèm `paper_full_technical.tex`, `paper_full_tables.tex` và `paper_historical_figures.tex`.

Bản rút gọn được tách thành `ecn_bench_paper_short.tex` / `.pdf`. `ecn_bench_paper_conf.tex` dàn trang hai cột cho bản rút gọn, không thay thế báo cáo đầy đủ. Bản gốc tháng 8 được giữ trong `../09_audit/`.

## Nội dung đã khôi phục và hoàn thiện

- Thiết kế benchmark, điều kiện A/B/C, rubric đủ 7 chiều, công thức, trọng số và grade bands; phân biệt specification với thang đo đã được kiểm chứng.
- Phương pháp thống kê, scoring, calibration, BSS, hiện tượng tương quan do dùng chung số hạng, và giới hạn power/độc lập.
- Source audit, micro-question mapping, schema bypass, retry/fallback, evaluator replication, transfer/truncation và baseline single-agent.
- Audit persona, outage, lỗi repair, catalogue/injection, sampled evidence, telemetry/JSD, kappa, missing traces và phân tích định tính từng trường hợp.
- Kiến trúc GraphRAG/custom Neo4j storage, serving/HPC/container/storage; đầy đủ ma trận N/R scaling, cross-model anchors, runtime và quyết định cấu hình với kết luận đã sửa. Snapshot phát hành không chứa dependency/import Graphiti.
- Danh mục 30 câu hỏi và bảng cho toàn bộ 360 unit của bốn campaign, tái tính từ vector thay vì chép bảng lỗi.
- Giữ đủ 30 hình của bản dài trong phụ lục có diễn giải sửa ngay cạnh từng hình. Hình cũ được ghi rõ là historical artifact, không được dùng p-value/claim bên trong làm kết quả hiện hành.

Khôi phục đầy đủ phạm vi nghiên cứu không có nghĩa chép lại các khẳng định sai thành kết luận hiện hành. Nội dung trùng lặp và các diễn giải không bảo vệ được đã được viết lại; bản gốc nguyên văn vẫn được bảo toàn. `FULL_RESTORATION_MAP.md` đối chiếu từng phần của bản cũ.

## Phát hiện thêm khi khôi phục bảng

Qwen2.5-14B/T1 vẫn hỏi về Fed thay vì câu hỏi UAW của các campaign khác, dù options và outcome trùng nhau. Đây là lỗi không thể phát hiện chỉ bằng kiểm tra vector xác suất.

- Giữ nguyên ba record T1 A/B/C trong dữ liệu và bảng tra cứu, ghi rõ sai question.
- Loại T1 khỏi cả bốn campaign khi lập các bảng tổng hợp aligned mở rộng: còn 29 sự kiện.
- Tập 20 sự kiện chính vốn không chứa T1: kết quả chính không thay đổi.
- Không chạy simulation để sửa T1 và không sửa dữ liệu nhằm giấu lỗi.

## Kiểm chứng

12/12 tests đạt tại workspace và release, gồm test về question collision, đủ 360 record, confidence bins và tính bất biến của source bytes. Hai script analysis chỉ đọc dữ liệu cũ; không gọi model, API hoặc HPC. Bảng full dùng cùng seed/bootstrap contract với phân tích chính khi cần interval.

Các bảng SQL scan và hình lịch sử được giữ đúng tư cách audit record; không tuyên bố đã tái chạy toàn bộ scan trên raw traces đã mất. Rà soát thống kê không biến dữ liệu quan sát thành bằng chứng nhân quả.

## Trước khi thực sự public

Thông tin tác giả, affiliation, email học thuật, giáo viên hướng dẫn và repository
private đã được xác nhận trong bản metadata 1.2.2. Trước khi chuyển repository sang
public, tác giả còn cần rà soát quyền phân phối và thông tin nhạy cảm trong artifact;
chỉ thêm DOI sau khi có định danh thật. Nếu chọn venue, cần chỉnh template/page
limit/anonymization riêng. Đây là bản đầy đủ theo hướng technical report/preprint;
không phải cam kết được phản biện chấp nhận.

Không cần thêm simulation để công bố đúng phạm vi audit hiện tại. Những thí nghiệm cần cho claim mạnh hơn được giữ trong phần future work, không được thực hiện hoặc lập lịch.
