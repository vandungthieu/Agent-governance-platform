Cấu Trúc Thư Mục Mục Tiêu
Dự án này được tổ chức theo mô hình AI agent control plane với các ranh giới dịch vụ (service boundaries) rõ ràng.

Các Dịch Vụ (Services)
service/api-gateway: Cổng vào công khai (public entrypoint), xác thực (auth), định tuyến, chuẩn hóa yêu cầu (request normalization)

service/agent-orchestrator: Lập kế hoạch, lựa chọn công cụ, thực thi quy trình (workflow), quản lý trạng thái agent

service/guardrail-service: Kiểm tra chính sách, bộ lọc an toàn, phát hiện rủi ro và thông tin cá nhân (PII)

service/audit-service: Lưu nhật ký kiểm toán (audit trail), ghi lại sự kiện, liên kết vết (trace correlation), bằng chứng tuân thủ

service/tool-registry: Dữ liệu đặc tả (metadata) của công cụ, phân quyền, chính sách thực thi

service/memory-service: Bộ nhớ ngắn hạn và dài hạn cho agent

Dùng Chung (Shared)
shared/contracts: Cấu trúc dữ liệu (schemas) cho request/response/event dùng chung giữa các dịch vụ

shared/events: Tên sự kiện và khung bao bọc tin nhắn (message envelopes)

shared/auth: Hỗ trợ xác thực, phân tích token, xử lý vai trò/tenant (role/tenant helpers)

shared/utils: Các tiện ích có thể tái sử dụng

Hạ Tầng (Infrastructure)
infra: File cấu hình triển khai (deployment manifests), Docker Compose, Kubernetes, và các mẫu môi trường (environment templates)

Kiểm Thử (Tests)
tests/unit: Kiểm thử đơn vị (unit test) cho từng dịch vụ

tests/integration: Kiểm thử tích hợp giữa các dịch vụ (integration test)

tests/e2e: Kiểm thử toàn trình (end-to-end workflow test)