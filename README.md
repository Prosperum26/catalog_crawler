# Bách Hóa Xanh Catalog Crawler (MVP)

Project crawler dữ liệu sản phẩm thực phẩm từ website [Bách Hóa Xanh](https://www.bachhoaxanh.com/) phục vụ cho bài toán nghiên cứu:
**Recipe RAG → Ingredient Matching → Product Catalog → Shopping Cart**.

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
