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
├── config.py             # Cấu hình network, timeout, delay, đường dẫn
├── main.py               # CLI entry point
├── urls.txt              # Danh sách URL mẫu để test
├── crawler/
│   ├── __init__.py
│   ├── http_client.py    # HTTP client (delay, timeout, retry, session)
│   ├── models.py         # Product dataclass & serialization
│   ├── parser.py         # Parsing logic (JSON-LD Schema.org & HTML fallback)
│   └── storage.py        # Lưu kết quả ra JSON và CSV (hỗ trợ Excel/DataGrip)
├── data/
│   ├── raw/              # Lưu file HTML gốc (nếu bật --save-raw)
│   └── processed/        # Chứa products.json và products.csv
└── tests/
    ├── __init__.py
    └── test_parser.py    # Unit tests sử dụng mock HTML fixtures
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

## 3. Cách chạy Crawler

### 3.1. Crawl một sản phẩm đơn lẻ (`--url`)

```bash
python main.py --url "https://www.bachhoaxanh.com/nuoc-mam/nuoc-mam-nam-ngu-phu-quoc-dam-dac-32-do-dam-chai-500ml"
```

### 3.2. Crawl danh sách URL từ file (`--urls`)

File `urls.txt` chứa danh sách các đường dẫn sản phẩm công khai (mỗi dòng một URL, hỗ trợ comment `#`).

```bash
python main.py --urls urls.txt
```

### 3.3. Các tham số bổ sung

- `--delay <giây>`: Điều chỉnh khoảng nghỉ giữa các request (mặc định: `1.5` giây để không làm phiền server).
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

Crawler đi kèm bộ test offline kiểm thử toàn bộ các hàm trích xuất dữ liệu mà không cần gọi ra Internet:

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
3. **Crawl theo danh sách URL tĩnh**:
   - Chưa tích hợp sitemap parser tự động để tự thu thập toàn bộ hàng nghìn URL theo danh mục.

### Đề xuất cho các version tiếp theo:
- **Tích hợp Sitemap Spider**: Đọc từ `https://www.bachhoaxanh.com/sitemapnew/sitemap-product` để lấy danh sách URL tự động theo ngành hàng (Gia vị, Thịt, Sữa, Rau củ).
- **Brand Extraction Pipeline**: Thêm module NER / Rule-based extractor trong bước Ingredient Matching để tách `brand` từ `name`.
- **Ghi nhận đơn vị chuẩn hóa (Normalization)**: Chuyển đổi các đơn vị như `500ml`, `1 lít`, `500g`, `1kg` sang hệ số chuẩn (gram/ml) phục vụ tính toán định lượng công thức nấu ăn (Recipe Matching).
