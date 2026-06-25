# Cost Analysis — Task Force 1 · CDO-05

<!-- Doc owner: CDO-05
     Status: Skeleton (W11 T6 Pack #1) → Measured actual (W12 T4 Pack #2)
     Word target: 800-1500 từ -->

---

## 1. Cost model per tenant (forecast)

CDO-05 chọn EKS-native angle. Chi phí chia làm 2 loại:
- **Fixed cost**: cluster EKS, node group, ALB, observability stack — chia đều cho tất cả tenant.
- **Variable cost**: DynamoDB, SQS, S3, Lambda, CloudWatch — tăng theo số lượng incident/alert thực tế.

| Component | AWS Service | Unit cost (ap-southeast-1) | Tenant avg usage/month | $/tenant/month (50 tenant) |
|---|---|---|---|---|
| EKS control plane | EKS | $0.10/hr | Shared / 50 tenant | ~$1.46 |
| Compute — node group | EC2 t3.medium × 2 | ~$0.052/hr/node | Shared / 50 tenant | ~$1.49 |
| API entry | ALB | ~$0.008/hr + LCU | Shared / 50 tenant | ~$0.12 |
| Alert ingestion | Lambda (Ingest) | $0.20/1M req | ~500 invocations | ~$0.01 |
| Event queue | SQS Standard | $0.40/1M msg | ~1000 messages | ~$0.01 |
| Incident state | DynamoDB on-demand | $1.25/M WCU, $0.25/M RCU | ~5000 WCU, ~10000 RCU | ~$0.01 |
| Audit storage | S3 Standard | $0.025/GB | ~0.5 GB evidence | ~$0.01 |
| Metrics | Prometheus (in-cluster) | Included in node cost | — | — |
| Logs | Loki (in-cluster) | Included in node cost | — | — |
| AWS-side monitoring | CloudWatch Logs | $0.76/GB ingested | ~0.2 GB | ~$0.15 |
| WAF (optional) | AWS WAF | ~$5/month base + $1/1M req | Shared / 50 tenant | ~$0.10 |
| VPC Endpoints | S3, DynamoDB, Secrets Manager, Bedrock | ~$0.01/hr/endpoint × 4 | Shared / 50 tenant | ~$0.06 |
| AI inference | Amazon Bedrock | <!-- TODO: SQ-05 chưa confirm --> | ~50 calls | <!-- TODO --> |
| **Total / tenant / month (est.)** | | | | **~$3.48 + Bedrock** |

> ⚠️ **TODO (fill W12)**: Bedrock cost chưa có — đang là open question SQ-05 trong `03_security_design.md`: "Bedrock có bật thật không? Model/cost cap là gì?" Cần AIO-01 confirm trước khi điền. Ước tính tạm nếu dùng Claude Haiku: ~$0.25/1M input token × 50 calls × 2000 token/call ≈ $0.025/tenant/month.
>
> ⚠️ **TODO (fill W12)**: WAF chỉ enable nếu ALB public internet. SQ-01 trong security design chưa confirm: "Public API/ALB có cần public internet thật không, hay chỉ demo internal?" Nếu internal only → WAF cost = $0.


---

## 2. Cost at scale

Fixed cost (EKS cluster, node group, ALB, observability stack) được chia đều cho tất cả tenant — per-tenant cost giảm khi số tenant tăng.

| Tenant count | EKS fixed ($/month) | Variable ($/month) | Total ($/month) | Avg per-tenant |
|---|---|---|---|---|
| 10 | ~$163 | ~$5 | ~$168 | ~$16.80 |
| 50 | ~$163 | ~$25 | ~$188 | ~$3.76 |
| 200 | ~$163 (scale node group) | ~$100 | ~$263 | ~$1.32 |

> ⚠️ **TODO (fill W12)**: Số node group cần scale khi >50 tenant chưa được đo thực tế. Sẽ update sau load test trong `07_test_eval_report.md`.

*Ghi chú: EKS fixed cost bao gồm control plane ($73/tháng) + 2 × t3.medium node (~$76/tháng) + ALB (~$8/tháng) + CloudWatch (~$6/tháng) + VPC Endpoints (~$3/tháng). WAF tính riêng nếu ALB public.*

---

## 3. Cost optimization applied

### Đã áp dụng trong MVP

- ✅ **2 environment thay vì 3** (dev + prod): Tiết kiệm ~$163/tháng so với chạy 3 cluster đầy đủ. Dev environment đóng vai trò staging, giảm fixed cost trong budget $100–150 / 2 tuần. (ADR-004 §0.4)
- ✅ **DynamoDB on-demand**: Không cần ước lượng provisioned capacity trước — phù hợp với workload alert-driven không đều. Tránh overpay khi idle.
- ✅ **Prometheus + Loki in-cluster**: Chạy trong EKS node — không tốn thêm managed service cost. Dùng lại node đã có.
- ✅ **Lambda cho Ingest**: Chỉ tốn tiền khi có alert webhook thật — không chạy liên tục như ECS task.
- ✅ **S3 lifecycle policy**: Evidence cũ hơn 30 ngày → chuyển sang S3 IA (Infrequent Access), tiết kiệm ~40% storage cost. Cũ hơn 90 ngày → S3 Glacier.
- ✅ **CloudWatch log retention**: Set 7–14 ngày cho application log (theo security design §15), 14 ngày cho Lambda log — tránh tích lũy log không cần thiết. S3/DynamoDB evidence giữ 30–90 ngày theo retention policy.
- ✅ **VPC Endpoints cho S3, DynamoDB, Secrets Manager, Bedrock**: 4 endpoint — tránh traffic qua NAT Gateway, tiết kiệm ~$0.045/GB data transfer và tăng security (traffic không ra internet).
- ✅ **AI call gating trong Correlator Worker**: Không gọi AI mỗi alert. Chỉ gọi khi incident mới hoặc severity tăng — giảm Bedrock cost đáng kể.

### Chưa áp dụng (cost vs complexity trade-off)

- ☐ **Spot instances cho node group**: Tiết kiệm ~70% EC2 cost nhưng rủi ro interruption trong demo. Không phù hợp cho capstone environment cần stability. Xem xét post-capstone.
- ☐ **Reserved capacity**: Cần 1+ năm commit — không phù hợp cho 2 tuần build. Khuyến nghị sau 3 tháng production baseline.
- ☐ **Bedrock prompt caching**: Phụ thuộc AI group implement — CDO không control. Ghi chú để AI group xem xét.
- ☐ **KEDA (Kubernetes Event-driven Autoscaling)** theo SQS queue depth: Scale worker pod xuống 0 khi không có alert. Giảm node cost đáng kể. Chưa implement trong MVP do thời gian W11.

---

## 4. Cost vs alternatives (cùng task force)

TF1 có 2 CDO với angle khác nhau. CDO-05 chọn EKS-native, CDO còn lại chọn Serverless-first (Lambda-heavy).

| Angle | Fixed cost/month | Variable cost/month | Avg per-tenant (50 tenant) | Win axis |
|---|---|---|---|---|
| **CDO-05: EKS-native** | ~$163 (cluster + nodes) | Thấp (SQS, DynamoDB, Lambda nhỏ) | ~$3.76 | Ecosystem consistency, Observability depth, Production realism |
| **CDO khác: Serverless-first** | chưa biết | chưa biết | chưa biết | CDO khác chưa biết |

**Trade-off rõ ràng**:
- EKS-native có fixed cost cao hơn ($163/tháng cluster) nhưng per-invocation cost thấp hơn khi alert volume tăng. Break-even điểm khoảng 50–100 tenant.
- Serverless-first có fixed cost $0 nhưng per-alert cost cao hơn, đặc biệt khi alert storm xảy ra (50+ alert/phút × Lambda invocation cost).

> ⚠️ **TODO**: Xác nhận số liệu CDO kia khi có — để hoàn thiện bảng so sánh.

---

## 5. Measured actual (Pack #2 only — fill in W12)

### 5.1 2-week capstone spend

> ⚠️ **TODO (fill W12 T4)**: Section này fill sau khi build xong. Xem AWS Cost Explorer theo tag `Project=tf1-cdo05`.

| Service | Forecast 2 tuần | Actual | Delta |
|---|---|---|---|
| EKS control plane | ~$14 | — | — |
| EC2 node group (2× t3.medium) | ~$14.56 | — | — |
| ALB | ~$2 | — | — |
| Lambda (Ingest) | ~$0.50 | — | — |
| SQS | ~$0.10 | — | — |
| DynamoDB | ~$0.50 | — | — |
| S3 | ~$0.10 | — | — |
| CloudWatch | ~$2 | — | — |
| Bedrock | <!-- TODO --> | — | — |
| **Total** | **~$34 + Bedrock** | — | — |

### 5.2 Per-tenant actual

> ⚠️ **TODO (fill W12 T4)**: Measure sau khi onboard ≥3 tenant test và chạy load test.

| Tenant test | Service mix | $/day | Extrapolate $/month |
|---|---|---|---|
| tenant-a (small load) | ~5 alert/ngày | — | — |
| tenant-b (medium load) | ~20 alert/ngày | — | — |
| tenant-c (burst load) | ~50+ alert/ngày | — | — |

### 5.3 Cost-per-correct-decision (joint với AI eval)

> ⚠️ **TODO (fill W12 T4)**: Joint với AI group sau khi có eval report từ `../../ai/docs/04_eval_report.md`.

| Metric | Value |
|---|---|
| Total AI calls in capstone | — |
| Correct decisions (confidence ≥ 0.7, RCA verified) | — |
| Total Bedrock cost | — |
| **Cost per correct decision** | **—** |

---

## 6. Cost guardrails

Các cơ chế kiểm soát chi phí đã setup trong infrastructure:

- **CloudWatch Billing Alarm**: Alert khi monthly spend vượt $50 (70%), $75 (90%), $100 (100% budget).
- **Per-tenant AI call quota**: Correlator Worker enforce max 10 AI calls/incident. Skip gọi AI khi alert là duplicate hoặc chỉ update `last_seen_at` — bảo vệ Bedrock cost.
- **Bedrock daily spend cap**: CloudWatch Alarm theo metric `bedrock:InvokeModelCount` — alert khi vượt ngưỡng daily budget. Model allowlist chỉ cho phép model đã approve (SQ-05 confirm với AIO-01).
- **WAF rate-based rule**: Nếu ALB public, WAF rate limit bảo vệ khỏi spam alert webhook giả — tránh tăng Lambda invocation cost và tạo incident giả.
- **DLQ monitoring**: Alert khi DLQ có message — tránh silent retry loop tốn cost.
- **Log retention policy**: Enforced qua Terraform — CloudWatch/Loki 7–14 ngày, S3 evidence 30–90 ngày. Tự động xóa log cũ, tránh tích lũy cost.

---

## 7. Cost recommendations cho production

Sau capstone, nếu deploy production thật:

- **Reserved Instances (1 năm)**: Sau 3 tháng có usage baseline, mua RI cho EKS node group — tiết kiệm ~30–40% EC2 cost.
- **Savings Plan cho Fargate** (nếu sau này chuyển một số workload sang Fargate): Compute Savings Plan tiết kiệm ~20%.
- **KEDA scale-to-zero**: Enable KEDA cho Correlator Worker theo SQS queue depth — scale xuống 0 pod khi không có alert, giảm node count và EC2 cost.
- **Spot node group cho observability**: Prometheus, Loki, Grafana có thể chạy trên Spot node (chấp nhận disruption) — tiết kiệm ~70% node cost cho observability layer.
- **Cross-region replication**: Chỉ enable S3 cross-region cho enterprise tier tenant — không replication đại trà.
- **Bedrock prompt caching**: Enable sau khi AI group stable — giảm input token cost đáng kể cho repeated context pattern.

---

## Related documents

- [`01_requirements_analysis.md`](01_requirements_analysis.md) — NFR targets (budget $100–150/2 tuần, 50 tenant scale) driving cost model
- [`02_infra_design.md`](02_infra_design.md) — Component list (EKS, ALB, SQS, DynamoDB, S3, Lambda) là nguồn dữ liệu cho §1
- [`04_deployment_design.md`](04_deployment_design.md) — 2-env strategy (§0.4) là quyết định cost lớn nhất
- [`07_test_eval_report.md`](07_test_eval_report.md) — Load test results validate cost assumptions trong §5
- [`08_adrs.md`](08_adrs.md) — ADR-001 (EKS), ADR-002 (DynamoDB on-demand) giải thích cost trade-off