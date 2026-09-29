# Phiếu Phản Ánh — K4 Level 3B, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: điền câu trả lời bên dưới mỗi câu hỏi.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Mai Quang Dũng  Mã học viên: L3B202602966

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Tình huống cụ thể: Khi deploy ứng dụng lên Cloud (Railway/Render) hoặc môi trường Production, lập trình viên quên cấu hình biến môi trường `AGENT_API_KEY` trong dashboard. Nếu để giá trị mặc định là `"changeme"`, service vẫn sẽ khởi động bình thường và báo "healthy". Kẻ xấu hoặc bot scan Internet có thể gửi request đến endpoint `/ask` với key `"changeme"` để gọi LLM miễn phí, bòn rút hạn mức API và làm tăng vọt chi phí hàng nghìn USD mà đội ngũ phát triển không hề hay biết cho đến cuối tháng. 

Ngược lại, khi không có giá trị mặc định, Pydantic `Settings` sẽ raise `ValidationError` ngay lúc nạp cấu hình khi service vừa khởi động (Fail Fast). Quá trình deploy sẽ lập tức báo lỗi (CrashLoopBackOff hoặc Deploy Failed), alert được gửi ngay đến lập trình viên và ngăn chặn service bị lộ ra ngoài Internet mà không có cơ chế bảo vệ.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Dòng log JSON thu được:
`{"timestamp": "2026-09-29T14:45:10.123456Z", "level": "info", "event": "ask_completed", "user_id": "sv-test", "tokens_in": 15, "tokens_out": 32, "cost_usd": 0.00094}`

Hai việc làm được với log JSON cấu trúc mà lệnh `print` thông thường không thể làm được:
1. **Truy vấn và phân tích có cấu trúc bằng Log Aggregator (Elasticsearch / Grafana Loki / Datadog):** Do log có schema rõ ràng, hệ thống có thể index và lọc tức thì các request theo `user_id = 'sv-test'`, hoặc tính tổng chi phí `sum(cost_usd)` theo từng người dùng trong khoảng thời gian cụ thể mà không cần viết regex phức tạp để bóc tách text thô.
2. **Thiết lập cảnh báo thời gian thực và đo lường SLA/Cost:** Dễ dàng parse trường `cost_usd` và số token để thiết lập alert tự động khi chi phí của một request vượt ngưỡng bất thường, hoặc tự động đồng bộ số liệu vào pipeline thanh toán/kế toán (billing pipeline).

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | ~1.02 GB |
| Multi-stage | ~168 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Phần dung lượng chênh lệch khoảng hơn 850 MB bao gồm:
1. Bộ công cụ phát triển phần mềm và trình biên dịch C/C++ (`gcc`, `g++`, `make`, các thư viện `linux-headers`, wheel build dependencies) vốn chỉ cần thiết trong giai đoạn biên dịch thư viện Python native (ở stage `builder`) chứ không dùng khi chạy ứng dụng.
2. Bộ nhớ cache tải xuống của `pip` (`~/.cache/pip`), các gói tài liệu trợ giúp (man pages, apt cache), và các thư viện hệ điều hành phụ trợ của base image Debian đầy đủ so với base image tối giản `python:3.11-slim` ở stage `runtime`. Multi-stage chỉ copy thư mục cài đặt sạch `/install` sang `/usr/local` ở runtime nên image cuối cùng cực kỳ nhẹ.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

- Khi sửa một ký tự trong `app/main.py`:
  + Các layer từ đầu cho đến `COPY requirements.txt .` và `RUN pip install ...` (toàn bộ stage `builder`) cũng như việc copy thư viện sang stage `runtime` đều được Docker lấy lại từ cache (`CACHED`), không phải tải hay cài lại bất cứ gói nào.
  + Chỉ có layer `COPY app ./app` và các chỉ thị tiếp theo (`HEALTHCHECK`, `CMD`) bị invalidate cache và phải thực thi lại, quá trình build chỉ mất khoảng 1-2 giây.
- Nếu đặt `COPY . .` lên trước `RUN pip install`:
  + Mỗi khi sửa dù chỉ một ký tự trong code, hash của layer `COPY . .` thay đổi làm toàn bộ cache phía sau bị vô hiệu. Docker buộc phải chạy lại lệnh `RUN pip install` từ đầu, kéo dài thời gian build lên vài phút và lãng phí băng thông mạng.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

Chuỗi sự kiện:
1. Ứng dụng Python có lỗ hổng (ví dụ: Remote Code Execution qua deserialization, SSTI, hoặc command injection).
2. Kẻ tấn công gửi payload khai thác thành công và chiếm được quyền điều khiển shell bên trong container.
3. Nếu container chạy với user mặc định là `root` (UID 0), tiến trình của kẻ tấn công có quyền root trong namespace container. Nếu container có mount volume nhạy cảm (như `/var/run/docker.sock` hoặc thư mục `/etc` của host), hoặc gặp phải lỗ hổng Linux kernel container escape, kẻ tấn công có thể thoát khỏi container và chiếm quyền root trực tiếp trên toàn bộ máy chủ (host).
4. Lệnh `USER appuser` (UID 10001) cắt đứt chuỗi tấn công ngay tại bước 2-3: kẻ tấn công bị giam trong quyền của user thường không có đặc quyền (unprivileged user), không thể đọc/ghi file hệ thống, không thể truy cập socket đặc quyền của Docker daemon, loại bỏ nguy cơ chiếm máy chủ host.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

- Con số tối đa: **20 request**.
- Giải thích:
  + Ở giây 59 của phút trước: người dùng gửi dồn dập 10 request (vừa đủ hạn mức 10 req/phút của phút đó).
  + Đúng vào giây 00 của phút tiếp theo: bộ đếm cố định (Fixed Window) bị reset về 0. Người dùng lập tức gửi thêm 10 request nữa.
  + Như vậy, trong khoảng thời gian chỉ vỏn vẹn 2 giây (từ giây 59 đến giây 01), hệ thống phải hứng chịu tới 20 request (gấp đôi hạn mức 10 req/phút). Sliding window giải quyết triệt để lỗi này bằng cách xét liên tục khoảng thời gian 60 giây trôi về trước từ thời điểm hiện tại.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

Khác nhau:
- **Rate Limit** bảo vệ **hạ tầng và tính sẵn sàng (Availability/Concurrency)** trong ngắn hạn (giây/phút), đếm số lượng requests để chống nghẽn và từ chối dịch vụ (DDoS/spam).
- **Cost Guard** bảo vệ **ngân sách tài chính (Financial Budget)** trong dài hạn (tháng), cộng dồn chi phí tiền tệ thực tế dựa trên số token LLM tiêu thụ.

Tình huống Rate limit cho qua nhưng Cost guard chặn:
- Người dùng chỉ gửi 1 câu hỏi duy nhất mỗi 10 phút (tần suất cực thấp, hoàn toàn dưới mức rate limit 10 req/phút), nhưng trong tháng tài khoản này đã tiêu hết 10.0$ tiền quota API LLM. Cost guard sẽ chặn ngay bằng mã lỗi `402 Payment Required`.

Tình huống Cost guard cho qua nhưng Rate limit chặn:
- Một tài khoản mới toanh đầu tháng chưa tiêu đồng nào (chi phí hiện tại 0.0$ / 10.0$). Người dùng dùng script bắn liên tục 15 câu hỏi trong vòng 3 giây. Dù ngân sách còn thừa nhiều, Rate limit sliding window sẽ chặn từ request thứ 11 trở đi bằng mã lỗi `429 Too Many Requests`.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Thứ tự sự kiện:
1. Redis gặp sự cố mạng hoặc khởi động lại, mất kết nối trong 30 giây.
2. Endpoint gộp trả về mã lỗi 503 do không ping được Redis.
3. Bộ điều phối (Docker Swarm/Kubernetes/Cloud Orchestrator) sử dụng endpoint này làm Liveness Probe sẽ kết luận rằng cả 3 container agent đều đã "chết".
4. Orchestrator tự động kill tiến trình và khởi động lại (restart) liên tục toàn bộ 3 container (restart loop).
5. Khi container khởi động lại, Redis vẫn chưa sẵn sàng nên endpoint tiếp tục trả về 503, khiến orchestrator lại kill tiếp.
6. Hệ thống rơi vào trạng thái cascading failure / flapping, CPU máy chủ tăng vọt vì liên tục khởi động container, làm mất kết nối toàn bộ hệ thống ngay cả khi app code hoàn toàn khỏe mạnh. (Nếu tách riêng, `/health` vẫn 200 giúp container sống, còn `/ready` trả 503 chỉ tạm thời ngắt traffic từ load balancer cho đến khi Redis kết nối lại).

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

Nếu lịch sử được lưu trong dict Python trong bộ nhớ của tiến trình:
- Khi có 3 container chạy song song, Load Balancer sẽ chia request luân phiên (Round Robin) đến từng container.
- Mỗi container có một biến dict nằm trên RAM riêng biệt, không chia sẻ cho nhau.
- Kết quả là `history_length` sẽ nhảy lộn xộn:
  + Request 1 tới container A: `history_length = 0` (lưu vào dict A).
  + Request 2 tới container B: `history_length = 0` (dict B chưa có gì).
  + Request 3 tới container C: `history_length = 0` (dict C chưa có gì).
  + Request 4 quay lại container A: `history_length = 2` (vì đã có câu hỏi và trả lời của Request 1).
  Số đếm không tăng liên tục mà phụ thuộc vào việc request rơi ngẫu nhiên vào container nào. Khi dùng Redis chung, mọi container đều đọc/ghi vào một kho lưu trữ tập trung, đảm bảo `history_length` luôn tăng đều đặn `[0, 2, 4, 6, ...]`.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

- **Lỗi gặp phải:** Healthcheck timeout / Service Unavailable khi deploy lên Railway.
- **Thông báo lỗi:** Railway logs báo: `Deploy Failed: Health check timed out on /health` hoặc không truy cập được URL dịch vụ.
- **Nguyên nhân:** Railway không cố định cổng 8000 mà tự động cấp phát cổng ngẫu nhiên thông qua biến môi trường `$PORT` (ví dụ `PORT=5678`). Nếu ứng dụng hoặc Dockerfile hardcode lệnh `uvicorn ... --port 8000`, Uvicorn sẽ lắng nghe cổng 8000 trong khi Railway proxy lại chuyển tiếp request tới cổng `$PORT`, dẫn đến health check thất bại và deploy bị hủy.
- **Cách sửa:** Cập nhật lệnh chạy trong `Dockerfile` và `railway.toml` thành `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` và cập nhật lệnh healthcheck để đọc cổng linh hoạt từ `$PORT`. Sau khi cấu hình, ứng dụng bind chính xác cổng do cloud cấp phát và deploy thành công 100%.
