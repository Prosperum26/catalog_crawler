# Bách Hóa Xanh Catalog Crawler (MVP)

Project crawler dữ liệu sản phẩm thực phẩm từ website [Bách Hóa Xanh](https://www.bachhoaxanh.com/) phục vụ cho bài toán nghiên cứu:
**Recipe RAG → Ingredient Matching → Product Catalog → Shopping Cart**.

> **Lưu ý quan trọng:** Đây là phần mềm mã nguồn mở phục vụ mục đích nghiên cứu và phát triển. Người sử dụng tự chịu trách nhiệm bảo đảm việc sử dụng crawler, các URL được truy cập và dữ liệu được lưu trữ/phân phối là hợp pháp tại nơi mình hoạt động.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Cấu trúc Project

```text
catalog_crawler/
├── README.md
├── requirements.txt
├── .gitignore
├── config.py             # Cấu hình network, timeout, delay, sitemaps, đường dẫn
├── main.py               # CLI entry point (Crawl + Tự động Discovery)
├── urls.txt              # Danh sách URL mẫu để test
├── crawler/
│   ├── __init__.py
│   ├── discovery.py      # Tự động quét và phát hiện URL từ XML Sitemaps
│   ├── http_client.py    # HTTP client (delay, timeout, retry, session)
│   ├── models.py         # Product dataclass & serialization
│   ├── parser.py         # Parsing logic (JSON-LD Schema.org & HTML fallback)
│   └── storage.py        # Lưu kết quả ra JSON và CSV (hỗ trợ Excel/DataGrip)
├── data/
│   ├── raw/              # Lưu file HTML gốc (nếu bật --save-raw)
│   └── processed/        # Chứa products.json và products.csv
└── tests/
    ├── __init__.py
    ├── test_discovery.py # Unit tests cho Sitemap URL Discovery
    └── test_parser.py    # Unit tests cho HTML/JSON-LD Parser
```

---

## 2. Cài đặt môi trường

Yêu cầu: **Python 3.11+**.

### Bước 1: Tạo và kích hoạt Virtual Environment

Trên Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Trên Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 2: Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

Các thư viện chính:
- `requests`: Thực hiện HTTP GET requests đơn giản, ổn định.
- `beautifulsoup4`: Phân tích HTML DOM và trích xuất JSON-LD scripts.
- `pytest`: Chạy bộ unit tests với mock fixtures offline.

---

## 3. Cách sử dụng

### 3.1. Thu thập URL tự động từ Sitemap (`--discover`)

Không cần nhập link bằng tay, crawler có thể tự động duyệt cây XML Sitemap của Bách Hóa Xanh (`/sitemapnew/sitemap-product`) và lọc chỉ lấy sản phẩm thực phẩm:

```bash
# Tự động quét 50 URL thực phẩm đầu tiên và lưu vào urls.txt
python main.py --discover --limit 50

# Quét tất cả URL phù hợp trong toàn bộ sitemap
python main.py --discover --all-urls

# Quét URL của một ngành hàng thực phẩm cụ thể (ví dụ: nước mắm)
python main.py --discover --category nuoc-mam --limit 20

# Quét ngành hàng dầu ăn và lưu ra file chỉ định
python main.py --discover --category dau-an --limit 30 --output-urls data/dau_an_urls.txt

# Vừa tự động phát hiện URL vừa cào dữ liệu luôn trong một lệnh
python main.py --discover --category sua-tuoi --limit 10 --crawl
```

Các tùy chọn cho `--discover`:
- `--limit <số lượng>`: Giới hạn số lượng URL muốn lấy (mặc định: `50`).
- `--all-urls`: Bỏ giới hạn số lượng, duyệt tất cả sitemap con và lấy mọi URL phù hợp bộ lọc.
- `--category <slug>`: Lọc theo ngành hàng (ví dụ: `nuoc-mam`, `dau-an`, `sua-tuoi`, `gao`, `thit-heo`...).
- `--output-urls <đường dẫn>`: File lưu danh sách URL (mặc định: `urls.txt`).
- `--crawl`: Kích hoạt cào dữ liệu ngay sau khi quét xong URL.
- `--all-categories`: Cho phép lấy cả các ngành hàng phi thực phẩm (hóa phẩm, gia dụng). Mặc định hệ thống tự động loại trừ các mặt hàng phi thực phẩm.

---

### 3.2. Crawl theo danh sách URL (`--urls`) hoặc đơn lẻ (`--url`)

```bash
# Crawl toàn bộ link trong file urls.txt
python main.py --urls urls.txt

# Crawl 1 sản phẩm đơn lẻ
python main.py --url "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-phu-quoc-dam-dac-32-do-dam-chai-500ml"
```

### 3.3. Các tham số crawl bổ sung

- `--delay <giây>`: Khoảng nghỉ giữa các request (mặc định: `1.5` giây để không làm phiền server).
- `--save-raw`: Lưu bản sao HTML thô vào thư mục `data/raw/` phục vụ debug/re-parse sau này.
- `--overwrite`: Ghi đè file output thay vì merge với các sản phẩm đã crawl trước đó.

Ví dụ:
```bash
python main.py --urls urls.txt --delay 2.0 --save-raw
```

---

## 4. Vị trí & Định dạng Output

Dữ liệu sau khi crawl được tự động xuất ra 2 file trong `data/processed/`:

1. `data/processed/products.json`:
   - Định dạng JSON UTF-8 với `indent=2, ensure_ascii=False`.
   - Sẵn sàng nạp vào các pipeline Embeddings, Vector Database hoặc Matching logic.

2. `data/processed/products.csv`:
   - Định dạng CSV với bảng mã `utf-8-sig` (UTF-8 with BOM), giúp hiển thị tiếng Việt có dấu chuẩn xác 100% khi mở trực tiếp bằng Microsoft Excel hoặc DataGrip/DBeaver.

### Cấu trúc Data Model:
```json
{
  "name": "Nước mắm Nam Ngư Phú Quốc đậm đặc 32 độ đạm chai 500ml",
  "brand": null,
  "category": "Nước mắm",
  "price": 71000,
  "unit": "chai 500ml",
  "product_url": "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-phu-quoc-dam-dac-32-do-dam-chai-500ml",
  "source": "bachhoaxanh",
  "crawled_at": "2026-09-24T14:59:36.964104+00:00"
}
```

*Nguyên tắc: Không suy đoán dữ liệu nếu trang không cung cấp (để giá trị `null`).*

---

## 5. Cách thêm Field mới

Nếu muốn thêm trường mới (ví dụ: `image_url`, `description`, `sku`):

1. **Cập nhật Model** trong `crawler/models.py`:
   ```python
   @dataclass
   class Product:
       ...
       image_url: Optional[str] = None
   ```
2. **Cập nhật Parser** trong `crawler/parser.py`:
   - Viết hàm parse tương ứng:
     ```python
     def parse_image_url(soup: BeautifulSoup, json_ld: Optional[dict]) -> Optional[str]:
         if json_ld and json_ld.get("image"):
             return str(json_ld["image"])
         return None
     ```
   - Gọi hàm này trong `parse_product_page(...)`.
3. **Cập nhật danh sách cột CSV** trong `crawler/storage.py`:
   - Thêm tên trường vào `CSV_FIELDNAMES`.
4. **Cập nhật Unit Test** trong `tests/test_parser.py` để đảm bảo test coverage.

---

## 6. Chạy Test

Bộ test offline kiểm thử toàn bộ parser và sitemap discovery mà không cần kết nối Internet:

```bash
pytest -v
```

---

## 7. Các hạn chế hiện tại & Hướng phát triển

### Hạn chế ở phiên bản MVP:
1. **Trang sản phẩm dạng SPA / RSC (Client-side rendering)**:
   - Các trang sản phẩm đang bán có sẵn Schema.org `Product` JSON-LD trong static HTML nên crawler trích xuất được ngay mà không cần JavaScript engine.
   - Tuy nhiên, một số trang đã hết hàng hoặc bị đổi URL slug có thể fallback về Next.js shell (`BAILOUT_TO_CLIENT_SIDE_RENDERING`) mà không có pre-rendered metadata trong static HTML.
2. **Dữ liệu Brand**:
   - Schema.org của Bách Hóa Xanh hiện tại thường không khai báo trường `brand` riêng rẽ (tên thương hiệu thường được gộp chung trong trường `name`). Do đó trường `brand` sẽ trả về `null` đúng theo nguyên tắc "không phỏng đoán".

### Đề xuất cho các version tiếp theo:
- **Brand Extraction Pipeline**: Thêm module NER / Rule-based extractor trong bước Ingredient Matching để tách `brand` từ `name`.
- **Ghi nhận đơn vị chuẩn hóa (Normalization)**: Chuyển đổi các đơn vị như `500ml`, `1 lít`, `500g`, `1kg` sang hệ số chuẩn (gram/ml) phục vụ tính toán định lượng công thức nấu ăn (Recipe Matching).
- **Tải ảnh sản phẩm**: Bóc tách `image_url` từ JSON-LD hoặc tải file ảnh lưu trữ cục bộ vào `data/images/`.

---

## 8. Pháp lý, quyền sử dụng và trách nhiệm

### 8.1. Phạm vi giấy phép

Mã nguồn do tác giả của repository này viết được phát hành theo [MIT License](LICENSE). Giấy phép này áp dụng cho **mã nguồn của dự án**, không mặc nhiên cấp quyền đối với:

- Nội dung, HTML, văn bản, hình ảnh, logo, tên thương mại hoặc dữ liệu của Bách Hóa Xanh hay các bên thứ ba.
- Các URL, sitemap, API, dịch vụ hoặc website mà người sử dụng lựa chọn để truy cập.
- Các file được tạo ra từ việc crawl, bao gồm `data/raw/`, `data/processed/` và các bản sao dữ liệu sản phẩm.

Các nội dung trên có thể chịu sự điều chỉnh của điều khoản sử dụng, chính sách robots, quyền sở hữu trí tuệ, quyền cơ sở dữ liệu, quy định bảo vệ dữ liệu cá nhân và pháp luật hiện hành. Cần kiểm tra các điều kiện đó trước khi crawl, lưu trữ, sử dụng thương mại hoặc phân phối dữ liệu.

### 8.2. Sử dụng có trách nhiệm

Khi sử dụng dự án, bạn cần:

1. Kiểm tra và tuân thủ `robots.txt`, điều khoản sử dụng và các yêu cầu kỹ thuật của website đích.
2. Chỉ truy cập các tài nguyên mà bạn có cơ sở hợp pháp để truy cập; không vượt qua CAPTCHA, paywall, cơ chế xác thực, giới hạn truy cập hoặc biện pháp bảo vệ kỹ thuật.
3. Giữ mức tải hợp lý. Crawler có delay mặc định `1.5` giây giữa các request và có retry; không nên giảm delay nếu chưa đánh giá tác động lên website đích.
4. Tôn trọng yêu cầu gỡ bỏ hoặc hạn chế truy cập từ chủ sở hữu website.
5. Kiểm tra dữ liệu trước khi công bố. Không công khai thông tin cá nhân, token, cookie, header nhạy cảm, hoặc nội dung được lưu từ trang đích nếu không có quyền phù hợp.
6. Xóa dữ liệu không còn cần thiết và không dùng dữ liệu crawl để gây hiểu nhầm rằng dự án được Bách Hóa Xanh tài trợ, xác nhận hoặc liên kết.

Repository này không tự động bảo đảm rằng mọi website hoặc mọi cách sử dụng đều được phép. Việc đặt một URL công khai trong sitemap không đồng nghĩa với việc mọi hình thức thu thập hoặc phân phối dữ liệu từ URL đó đều được cấp phép.

### 8.3. Dữ liệu đầu ra và nội dung bên thứ ba

Các file output chỉ là kết quả kỹ thuật của quá trình xử lý. Người sử dụng phải tự xác minh nguồn gốc, độ chính xác, thời điểm cập nhật và quyền sử dụng của từng trường dữ liệu trước khi đưa vào sản phẩm, cơ sở dữ liệu công khai hoặc dịch vụ thương mại.

Không nên commit dữ liệu crawl, HTML thô, hình ảnh hoặc nội dung có bản quyền vào repository công khai nếu chưa có quyền cần thiết. Kiểm tra lịch sử Git trước khi publish vì việc thêm file vào `.gitignore` không xóa các file đã được track trước đó.

### 8.4. Nhãn hiệu và không liên kết

“Bách Hóa Xanh” và các tên, logo, nhãn hiệu xuất hiện trong dữ liệu là tài sản của chủ sở hữu tương ứng. Dự án này không tuyên bố có quan hệ đối tác, được chứng thực, tài trợ hoặc liên kết với Bách Hóa Xanh. Tên thương hiệu chỉ được dùng để mô tả nguồn dữ liệu mà crawler hỗ trợ.

### 8.5. Tuyên bố miễn trừ trách nhiệm

Phần mềm được cung cấp theo nguyên trạng, không có bảo đảm về tính chính xác, tính sẵn sàng, tính hợp pháp của dữ liệu thu thập hoặc sự phù hợp cho một mục đích cụ thể. Tác giả không chịu trách nhiệm cho thiệt hại, gián đoạn dịch vụ, vi phạm điều khoản, hoặc khiếu nại phát sinh từ việc người khác sử dụng phần mềm hay dữ liệu đầu ra.

Nội dung này là hướng dẫn sử dụng có trách nhiệm, không phải tư vấn pháp lý. Khi triển khai cho mục đích thương mại, quy mô lớn hoặc tại khu vực pháp lý cụ thể, hãy tham khảo luật sư hoặc chuyên gia phù hợp.

## 9. Dependencies và giấy phép bên thứ ba

Dự án sử dụng các package được khai báo trong [requirements.txt](requirements.txt). Mỗi package có giấy phép và điều kiện riêng; việc sử dụng package không làm thay đổi giấy phép của mã nguồn dự án. Hãy kiểm tra metadata và file license của phiên bản package thực tế trước khi phân phối sản phẩm kèm theo dependencies.

## 10. Tác giả và đóng góp

Thông tin tác giả, liên hệ và quy tắc đóng góp có thể được bổ sung tại đây trước khi public repository. Không đưa API key, cookie, thông tin tài khoản, dữ liệu cá nhân hoặc dữ liệu crawl chưa được kiểm tra vào issue, pull request hay commit.

## 11. Checklist trước khi public

- Thay `[YOUR NAME OR ORGANIZATION]` trong [LICENSE](LICENSE) bằng tên chủ bản quyền thực tế.
- Kiểm tra lại điều khoản sử dụng và `robots.txt` của nguồn dữ liệu tại thời điểm sử dụng.
- Xóa hoặc rà soát `data/raw/`, `data/processed/`, `urls.txt` và các file crawl trước khi commit.
- Quét repository để bảo đảm không có API key, cookie, token, thông tin cá nhân hoặc file nội bộ.
- Chạy `python -m pytest -v` và kiểm tra nội dung output trước khi phân phối.
- Nếu dự án được dùng thương mại hoặc crawl quy mô lớn, xin đánh giá pháp lý riêng trước khi triển khai.
