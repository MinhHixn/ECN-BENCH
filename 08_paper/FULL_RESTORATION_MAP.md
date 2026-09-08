# Đối chiếu khôi phục bản dài

Nguồn nguyên văn được bảo toàn: `paper_archive/ecn_bench_paper_20260826.tex` và PDF cùng tên. Báo cáo hiện hành: `ecn_bench_paper.tex` cùng ba tệp phụ lục được input trực tiếp. Không dùng số trang làm lý do loại nội dung.

| Phần của bản dài cũ | Vị trí và cách xử lý trong bản đầy đủ |
|---|---|
| Introduction | Main Introduction; giữ ba câu hỏi nghiên cứu trong Full Protocol |
| Related Work | Main Related Work mở rộng; sửa bibliography và bổ sung nguồn nền tảng |
| Experimental and Benchmark Design | Main Testbed và appendix Experimental and Benchmark Design |
| Seven-Dimension Grading Framework | Khôi phục đủ D1–D7, công thức, trọng số, display grades; không gọi là construct đã validated |
| Statistical Inference and Econometric Validation | Main Measurement và Full Protocol; bỏ invalid exact test/observed-power inference |
| Anti-Confound Protocols and Weight Integrity | Full Protocol: intended controls, graph memory và context provenance |
| July Campaign at Face Value | Tái tạo bảng đầy đủ bằng paper_full_analysis.py; đồ thị cũ vào annotated historical register |
| Loss of Sharpness and Degenerate Consensus | Main paired audit và giải thích đúng sharpness/uniform/Brier trong Full Protocol |
| Source-Code Audit | Main mechanism section và Extended Source-Code and Extraction Audit |
| Evaluator Replication | Main fixed-evidence/repeatability; mở rộng pairing, retry, metric consistency và runtime provenance |
| Four Models / Five Reads | Main estimands/sensitivity và full per-record tables; sửa ngân sách đọc, stale reads và T1 |
| Volume / Schema / Transfer / Truncation | Main existing probes và phần mở rộng source audit; giữ toàn bộ hình tương ứng với lời giải thích đã sửa |
| Content-Sensitive Predictive Signal | Main exploratory results; giữ kết quả, không coi date filter là leakage-free |
| Single-Agent Baseline | Main CoT section và full aggregation-budget discussion |
| Discussion and Limitations | Main limitations cùng full run-integrity, kappa và telemetry discussion |
| Conclusion and Future Work | Main conclusion và Extended Follow-Up Programme; không đề xuất tự chạy thêm |
| Consolidated Errata | Correction Record và các correction đặt tại đúng nội dung; bản errata nguyên văn vẫn trong archive |
| Per-Event Brier Tables | Mở rộng từ ba lên bốn campaign, đủ 360 unit; thêm register câu hỏi và bảng primary/ensemble/evaluator C |
| Supporting Analysis and Run-Integrity Audit | Khôi phục chi tiết persona, outage/repair, action scans, evidence digest, SBE/SDE, coupling, cutoff/leakage và missing traces |
| System Architecture and Engineering | Appendix riêng: routing, multi-GPU isolation, container/bind mounts, storage và preservation |
| July Scaling Campaign | Khôi phục N/R matrices, cross-model anchors, runtime, hardware failures và decision criteria; bỏ optimum/15B boundary chưa chứng minh |
| Data Availability | Giữ provenance và reproducibility; không dùng DOI giả hoặc tuyên bố đã public |
| 30 original figures | Giữ đủ trong Historical Figure Register, mỗi hình có corrected interpretation; không âm thầm xóa hình hoặc làm mới p-value cũ |

Các kết quả định lượng hiện hành: `paper_results.json`, `paper_full_results.json`. Những thống kê cũ không thể tái xác nhận được từ raw collection đã mất được ghi rõ là historical scan, không biến thành số liệu mới. Bản rút gọn được giữ riêng để không lặp lại việc thay thế báo cáo dài bằng một bài 10 trang.
