# NĐ13/2023 Compliance Checklist - MedViet AI Platform

## Scope

- Hệ thống xử lý hồ sơ bệnh nhân dùng cho AI training, API nội bộ và báo cáo phân tích.
- Dữ liệu nhạy cảm gồm: họ tên, CCCD, số điện thoại, email, địa chỉ, ngày sinh, bệnh án và kết quả xét nghiệm.
- Mục tiêu kiểm soát: data minimization, consent, access control, encryption, auditability, breach response và data localization theo NĐ13/2023.

## Evidence Status Legend

- Done: đã có implementation/evidence trong repo hoặc tài liệu audit được định danh.
- Partial: có một phần control, nhưng chưa đủ bằng chứng để kết luận compliant.
- Planned: chưa có implementation/evidence; cần hoàn thành plan và thêm bằng chứng trước khi tick.

## A. Data Localization

- [ ] Patient data production chỉ được lưu trên hạ tầng đặt tại Việt Nam. Status: Planned.
  - Planned technical control: cấu hình database/object storage bằng region allowlist `VN`, chặn deploy resource ngoài Việt Nam bằng policy-as-code trong CI.
  - Evidence needed: IaC/cloud resource inventory, CI policy check, và deployment logs chứng minh storage region là `VN`.
- [ ] Backup cũng phải ở trong lãnh thổ Việt Nam. Status: Planned.
  - Planned technical control: backup bucket/volume dùng cùng region `VN`, tắt cross-region replication, bật retention và immutable backup tối thiểu 30 ngày.
  - Evidence needed: backup policy/config, restore drill report, và log xác nhận cross-region replication bị tắt.
- [ ] Log mọi transfer data ra ngoài nếu có. Status: Planned.
  - Planned technical control: API gateway và data export job ghi audit event gồm `actor`, `role`, `resource`, `action`, `data_classification`, `destination_country`, `request_id`, `timestamp`.
  - Evidence needed: audit middleware, append-only audit store, và test xác nhận request allow/deny đều tạo audit event.
- [x] Deny restricted patient data export ra ngoài Việt Nam bằng policy rule. Status: Partial.
  - Evidence: OPA rule trong `policies/opa_policy.rego` deny export `restricted` data nếu `destination_country != "VN"`.
  - Gap: rule hiện tại chưa kiểm tra ticket phê duyệt và chưa thay thế bằng chứng về storage/backup residency.

## B. Explicit Consent

- [ ] Thu thập consent trước khi dùng dữ liệu cho AI training. Status: Planned.
  - Planned technical control: tạo consent ledger với `patient_id`, `purpose`, `version`, `granted_at`, `source`, `status`.
  - API/data pipeline chỉ đưa record vào training set khi consent `status == "active"` và `purpose` bao gồm `ai_training`.
- [ ] Có mechanism để user rút consent và xử lý Right to Erasure. Status: Planned.
  - Planned technical control: endpoint nội bộ tạo erasure request, cập nhật consent `revoked_at`, loại bệnh nhân khỏi batch training kế tiếp và queue deletion/anonymization cho dữ liệu dẫn xuất.
- [ ] Lưu consent record với timestamp. Status: Planned.
  - Planned technical control: append-only consent table hoặc event log, timestamp chuẩn UTC, chỉ DPO/Security Admin được sửa trạng thái.
  - Evidence needed: schema migration, API/service tests, và sample consent audit trail.

## C. Breach Notification (72h)

- [ ] Có incident response plan. Status: Planned.
  - Planned technical control: runbook gồm detect, triage, contain, eradicate, recover, notify; mỗi incident có owner, severity, timeline và evidence.
  - Evidence needed: runbook file, incident severity matrix, và tabletop exercise record.
- [ ] Alert tự động khi phát hiện breach. Status: Planned.
  - Planned technical control: Prometheus/Grafana alerts cho bất thường truy cập, export lớn, nhiều lỗi 403/401, PII xuất hiện trong anonymized output và lỗi encryption/decryption.
  - Evidence needed: metrics instrumentation, alert rules, dashboard, và synthetic alert test.
- [ ] Quy trình báo cáo đến cơ quan có thẩm quyền trong 72h. Status: Planned.
  - Planned technical control: incident ticket tự tính deadline `detected_at + 72h`, escalation tới DPO, Legal và Security Lead; template báo cáo chứa phạm vi dữ liệu, số lượng subject, nguyên nhân, biện pháp khắc phục.
  - Evidence needed: notification template, escalation routing, và ticket workflow test.

## D. DPO Appointment

- [ ] Đã bổ nhiệm Data Protection Officer. Status: Planned.
  - Evidence needed: tên/role DPO, ngày bổ nhiệm, và tài liệu phê duyệt nội bộ.
- [ ] DPO có contact channel chính thức. Status: Planned.
  - Placeholder hiện tại: `dpo@medviet.example`; cần thay bằng email/kênh liên hệ thật trước khi tick.
- [ ] DPO chịu trách nhiệm phê duyệt data sharing, breach notification, consent policy và kiểm tra định kỳ access review. Status: Planned.
  - Evidence needed: RACI/charter và log phê duyệt/review định kỳ.

## E. Technical Controls Mapping

| NĐ13 Requirement | Technical Control | Status | Owner | Evidence / Gap |
|------------------|-------------------|--------|-------|----------------|
| Data minimization | PII detection/anonymization pipeline bằng Presidio, custom recognizer cho CCCD và số điện thoại Việt Nam | Done | AI Team | `src/pii/*`, `tests/test_pii.py` |
| Purpose limitation | Consent ledger kiểm tra mục đích `ai_training` trước khi đưa dữ liệu vào training pipeline | Planned | Product + Data Team | Chưa có consent schema/service/test |
| Right to Erasure | Revocation workflow loại subject khỏi training batch và xoá/anonymize dữ liệu dẫn xuất | Planned | Platform Team | Delete endpoint hiện tại chỉ simulate admin delete, chưa có erasure workflow |
| Data localization | VN-only storage/backup policy, OPA deny export restricted data ra ngoài Việt Nam | Partial | Infra Team | Có OPA export-deny rule; chưa có IaC/CI/storage/backup evidence |
| Access control | RBAC bằng Casbin cho API và ABAC/export guard bằng OPA | Partial | Platform Team | Casbin API RBAC có test; OPA export guard chưa được tích hợp vào API/export flow |
| Encryption | AES-256-GCM envelope encryption at rest, TLS 1.3 in transit, production KEK lưu trong KMS/HSM | Partial | Infra Team | Local `SimpleVault` có test AES-256-GCM; TLS và KMS/HSM là production gap |
| Audit logging | Structured audit middleware, append-only audit store, centralized log retention tối thiểu 12 tháng | Planned | Platform Team | Chưa có audit middleware/store/test |
| Breach detection | Prometheus/Grafana alert rules cho access anomaly, suspicious export, PII leakage và service errors | Planned | Security Team | Chưa có metrics/alerts/dashboard |
| Breach notification | 72h incident workflow, DPO escalation và notification template | Planned | Security + Legal | Chưa có runbook/template/ticket workflow evidence |
| Periodic review | Quarterly access review, policy test, restore drill và tabletop breach exercise | Planned | DPO + Security Team | Chưa có schedule/evidence records |

## F. Technical Solutions For Planned Controls

### 1. Audit Logging

Implementation plan:

- Thêm FastAPI middleware ghi audit event cho mọi endpoint đọc/xoá/export dữ liệu bệnh nhân.
- Chuẩn hoá schema log:

```json
{
  "timestamp": "2026-05-12T10:00:00Z",
  "request_id": "uuid",
  "actor": "alice",
  "role": "ml_engineer",
  "resource": "training_data",
  "action": "read",
  "decision": "allow",
  "data_classification": "restricted",
  "destination_country": "VN",
  "client_ip": "10.0.0.15"
}
```

- Không ghi plaintext PII vào log; chỉ ghi `patient_id` hoặc hash/pseudonym khi cần điều tra.
- Gửi log tới append-only storage hoặc SIEM/Loki, bật retention tối thiểu 12 tháng và chỉ Security/DPO được đọc.
- Viết test để xác nhận request bị deny vẫn tạo audit event với `decision = "deny"`.
- Definition of done: 100% route nhạy cảm có audit event, log không chứa CCCD/email/số điện thoại thật, truy vấn được theo `request_id` trong vòng 5 phút.

### 2. Consent And Purpose Limitation

Implementation plan:

- Thêm consent ledger table/file với `patient_id`, `purpose`, `version`, `granted_at`, `source`, `status`, `revoked_at`.
- Thêm service function `has_active_consent(patient_id, "ai_training")`.
- Lọc training/anonymized dataset dựa trên consent active trước khi trả về hoặc đưa vào pipeline.
- Viết tests cho các case: consent active được include, revoked/expired/missing consent bị exclude.
- Definition of done: mọi record trong training set có consent active, có audit trail cho thay đổi consent, và có report số lượng record bị loại do thiếu consent.

### 3. Right To Erasure

Implementation plan:

- Thay delete simulation bằng erasure request workflow có trạng thái `requested`, `approved`, `completed`, `rejected`.
- Cập nhật consent `revoked_at` khi có request hợp lệ.
- Queue deletion/anonymization cho raw data, derived data, reports, và model/training artifacts nếu applicable.
- Ghi audit event cho mọi bước và gán owner/SLA.
- Definition of done: erasure request có test end-to-end, subject bị loại khỏi batch training kế tiếp, và có evidence log cho completion.

### 4. Data Localization Evidence

Implementation plan:

- Thêm IaC/policy-as-code rule validate storage/database/backup region chỉ thuộc allowlist `VN`.
- Thêm CI job chạy policy test khi thay đổi IaC/deployment config.
- Mở rộng OPA/export flow để yêu cầu `approval_ticket_id` cho restricted export, ngay cả khi destination là `VN`.
- Definition of done: CI fail khi resource ngoài `VN`, backup config được verify, và export restricted data cần OPA allow + ticket approval.

### 5. Breach Detection

Implementation plan:

- Bổ sung Prometheus metrics cho API:
  - `medviet_api_requests_total{role,resource,action,decision}`
  - `medviet_api_forbidden_total{role,resource}`
  - `medviet_data_export_records_total{role,destination_country}`
  - `medviet_pii_leakage_detected_total{pipeline}`
  - `medviet_encryption_failures_total{operation}`
- Tạo Grafana dashboard cho access denials, raw patient data reads, export volume và anonymization leakage.
- Tạo alert rules:
  - nhiều hơn 5 lần deny trong 10 phút với cùng actor;
  - bất kỳ export restricted data tới `destination_country != "VN"`;
  - raw patient data read ngoài giờ làm việc hoặc bởi role không phải `admin`;
  - PII còn xuất hiện trong output anonymized;
  - encryption/decryption failure tăng bất thường.
- Alert gửi tới Security Team và DPO qua Slack/email/on-call, tạo incident ticket tự động với deadline 72h.
- Definition of done: alert được test bằng synthetic event, có dashboard, có incident ticket mẫu và runbook xử lý tương ứng.

### 6. Breach Notification

Implementation plan:

- Tạo incident response runbook và template notification 72h.
- Thêm incident ticket fields: `detected_at`, `severity`, `affected_subject_count`, `data_scope`, `root_cause`, `containment`, `notification_deadline`, `owner`.
- Tự động tính `notification_deadline = detected_at + 72h` và escalate nếu còn dưới 24h.
- Definition of done: có tabletop exercise record, ticket mẫu, và notification template được DPO/Legal approve.

### 7. DPO And Periodic Review

Implementation plan:

- Cập nhật DPO appointment với tên/role/email thật và ngày hiệu lực.
- Tạo quarterly access review checklist cho Casbin policy, OPA policy, backup restore drill, và breach tabletop.
- Lưu review evidence trong `reports/` với date, reviewer, findings, remediation owner và due date.
- Definition of done: DPO charter có approval, review schedule tồn tại, và mỗi review tạo evidence record.
