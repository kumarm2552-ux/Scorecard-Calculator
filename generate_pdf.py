import io
import urllib.request
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import textwrap

class DryDraw:
    def line(self, *a, **kw): pass
    def rectangle(self, *a, **kw): pass
    def text(self, *a, **kw): pass

class PDFDraw:
    def __init__(self, c, height):
        self.c = c
        self.h = height

    def line(self, coords, fill, width=1):
        x0, y0, x1, y1 = coords
        self.c.setStrokeColorRGB(fill[0]/255, fill[1]/255, fill[2]/255)
        self.c.setLineWidth(width)
        self.c.line(x0, self.h - y0, x1, self.h - y1)

    def rectangle(self, coords, outline=None, width=1, fill=None):
        x0, y0, x1, y1 = coords
        if fill:
            if isinstance(fill, str):
                if fill == "white": fill = (255,255,255)
                elif fill == "black": fill = (0,0,0)
            if hasattr(fill, "__iter__"):
                self.c.setFillColorRGB(fill[0]/255, fill[1]/255, fill[2]/255)
        else:
            self.c.setFillColorRGB(1,1,1)

        if outline:
            self.c.setStrokeColorRGB(outline[0]/255, outline[1]/255, outline[2]/255)
            self.c.setLineWidth(width)
        else:
            self.c.setStrokeColorRGB(0,0,0)

        # rect(x, y, width, height) where y is from bottom
        self.c.rect(x0, self.h - y1, x1 - x0, y1 - y0, stroke=1 if outline else 0, fill=1 if fill else 0)
        self.c.setFillColorRGB(0,0,0) # reset

    def text(self, coords, text, fill="black", font_size=16, font_name="Helvetica", anchor=None):
        x, y = coords
        self.c.setFont(font_name, font_size)
        self.c.setFillColorRGB(0,0,0)
        
        baseline_y = self.h - (y + font_size * 0.8)

        if anchor == "mm":
            baseline_y = self.h - (y + font_size * 0.3)
            self.c.drawCentredString(x, baseline_y, str(text))
        elif anchor == "lm":
            baseline_y = self.h - (y + font_size * 0.3)
            self.c.drawString(x, baseline_y, str(text))
        else:
            self.c.drawString(x, baseline_y, str(text))

def get_image_size(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            b_data = response.read()
            ir = ImageReader(io.BytesIO(b_data))
            return ir, ir.getSize()
    except:
        return None, (0,0)

def draw_all(data, d_obj, width, banner_h, banner_img):
    y = 120
    top_box_y = 120
    if banner_img:
        if hasattr(d_obj, 'c'):
            d_obj.c.drawImage(banner_img, 0, d_obj.h - banner_h - 50, width, banner_h)
        top_box_y = banner_h + 80
    else:
        d_obj.text((width//2, 40), "रेल भर्ती बोर्ड / RAILWAY RECRUITMENT BOARDS", font_size=25, font_name="Helvetica-Bold", anchor="mm")
        
    border_color = (0, 0, 0)
    top_box_x1 = 50
    top_box_x2 = width - 50

    exam_name = data.get("exam_name", "Test Score Card").upper()
    board_name = "RAILWAY RECRUITMENT BOARD" if "RRB" in exam_name else "EXAMINATION BOARD"
    if "SSC" in exam_name: board_name = "STAFF SELECTION COMMISSION"
    
    d_obj.rectangle([top_box_x1, top_box_y, top_box_x2, top_box_y+30], outline=border_color, width=1)
    d_obj.text((width//2, top_box_y+15), board_name, font_size=20, font_name="Helvetica", anchor="mm")
    
    d_obj.rectangle([top_box_x1, top_box_y+30, top_box_x2, top_box_y+60], outline=border_color, width=1)
    d_obj.text((width//2, top_box_y+45), exam_name, font_size=20, font_name="Helvetica", anchor="mm")

    d_obj.text((width//2, top_box_y+85), " Candidate Score Card", font_size=28, font_name="Helvetica-Bold", anchor="mm")

    t_x1 = 50
    t_x2 = width - 50
    x_mid = 430
    y = top_box_y + 110

    def draw_row(key, val, font_size=18, font_name="Helvetica"):
        nonlocal y
        key_lines = textwrap.wrap(str(key), width=38)
        val_lines = textwrap.wrap(str(val), width=38)
        
        h = max(len(key_lines), len(val_lines)) * 26 + 10
        if h < 35: h = 35
        
        d_obj.rectangle([t_x1, y, t_x2, y+h], outline=border_color, width=1)
        d_obj.line([x_mid, y, x_mid, y+h], fill=border_color, width=1)
        
        center_row_y = y + h // 2
        
        tk_h = len(key_lines) * 26
        for idx, k in enumerate(key_lines):
            line_y = center_row_y - (tk_h // 2) + (idx * 26) + 13
            d_obj.text((t_x1+10, line_y), k, font_size=font_size, font_name=font_name, anchor="lm")
            
        tv_h = len(val_lines) * 26
        for idx, v in enumerate(val_lines):
            line_y = center_row_y - (tv_h // 2) + (idx * 26) + 13
            d_obj.text((x_mid+10, line_y), v, font_size=font_size, font_name=font_name, anchor="lm")
            
        y += h

    box_h = 100
    d_obj.rectangle([t_x1, y, t_x2, y+box_h], outline=border_color, width=1)
    d_obj.line([x_mid, y, x_mid, y+box_h], fill=border_color, width=1)
    
    photo_b64 = data.get("photo_b64", "")
    photo_url = data.get("photo_url", "")
    try:
        pio = None
        if photo_b64:
            header, encoded = photo_b64.split(",", 1)
            photo_data = base64.b64decode(encoded)
            pio = io.BytesIO(photo_data)
        elif photo_url:
            req = urllib.request.Request(photo_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                p_data = response.read()
                pio = io.BytesIO(p_data)
                
        if pio and hasattr(d_obj, 'c'):
            ir = ImageReader(pio)
            pw, ph = ir.getSize()
            target_h = 80
            target_w = int((pw / ph) * target_h)
            px = t_x1 + 10
            py = y + 10
            d_obj.c.drawImage(ir, px, d_obj.h - target_h - py, target_w, target_h)
    except:
        pass
    y += box_h
    
    draw_row("Registration Number", data.get("reg_no", "N/A"))
    draw_row("Roll Number", data.get("roll_no", "N/A"))
    draw_row("Name of the Candidate", data.get("cand_name", "N/A"))
    draw_row("Community", data.get("community", "N/A"))
    draw_row("Date of Exam", data.get("test_date", "N/A"))
    draw_row("Date of Exam Time", data.get("test_time", "N/A"))
    draw_row("Test Centre Name", data.get("test_center", "N/A"))
    draw_row("Name of Examination", data.get("exam_name", "N/A"))
    
    draw_row("Total No. of Questions", data.get("overall_total", ""))
    draw_row("Total No. of questions attempted", str(data.get("overall_attempted", "")))
    draw_row("No. of Question answered correctly", str(data.get("overall_correct", "")))
    draw_row("No. of Question answered incorrectly", str(data.get("overall_incorrect", "")))
    
    overall_total = data.get('overall_total', '100')
    overall_score = data.get('overall_score', 0)
    score_str = f"{overall_score:.2f}".rstrip("0").rstrip(".") if isinstance(overall_score, (float, int)) else str(overall_score)
    draw_row(f"Total Raw Marks out of {overall_total}", score_str, font_size=18, font_name="Helvetica-Bold")

    sections = data.get("sections", [])
    num_sections = len(sections)
    
    if num_sections > 1:
        y += 15 # Add some gap before section analysis
        
        d_obj.rectangle([t_x1, y, t_x2, y+30], outline=border_color, width=1, fill=(235, 235, 235))
        d_obj.text((width//2, y+15), "Section Wise Details", font_size=18, font_name="Helvetica-Bold", anchor="mm")
        y += 30
        
        d_obj.rectangle([t_x1, y, t_x2, y+30], outline=border_color, width=1, fill=(245, 245, 245))
        x_offsets = [250, 90, 100, 105, 105, 100]
        curr_x = t_x1
        headers = ["Section Name", "Total", "Attempt", "Right", "Wrong", "Marks"]
        
        for i, (w, text) in enumerate(zip(x_offsets, headers)):
            if i > 0:
                d_obj.line([curr_x, y, curr_x, y+30], fill=border_color, width=1)
            d_obj.text((curr_x + w//2, y+15), text, font_size=15, font_name="Helvetica-Bold", anchor="mm")
            curr_x += w
        y += 30

        total_q, total_att, total_right, total_wrong, total_marks = 0, 0, 0, 0, 0.0
        for sec in sections:
            sec_n = str(sec.get('name', 'Section'))
            s_tot = int(sec.get('total', 0))
            s_att = int(sec.get('right', 0)) + int(sec.get('wrong', 0))
            s_rt = int(sec.get('right', 0))
            s_wr = int(sec.get('wrong', 0))
            s_mk = float(sec.get('marks', 0))
            
            total_q += s_tot
            total_att += s_att
            total_right += s_rt
            total_wrong += s_wr
            total_marks += s_mk
            
            sec_lines = textwrap.wrap(sec_n, width=28)
            h = max(30, len(sec_lines)*16 + 10)
            
            vals = [sec_lines, str(s_tot), str(s_att), str(s_rt), str(s_wr), str(round(s_mk, 2))]
            
            d_obj.rectangle([t_x1, y, t_x2, y+h], outline=border_color, width=1)
            curr_x = t_x1
            for i, (w, content) in enumerate(zip(x_offsets, vals)):
                if i > 0:
                    d_obj.line([curr_x, y, curr_x, y+h], fill=border_color, width=1)
                if i == 0:
                    tk_h = len(content) * 16
                    center_row_y = y + h // 2
                    for line_idx, line in enumerate(content):
                        line_y = center_row_y - (tk_h // 2) + (line_idx * 16) + 8
                        d_obj.text((curr_x + 6, line_y), line, font_size=15, font_name="Helvetica", anchor="lm")
                else:
                    d_obj.text((curr_x + w//2, y+h//2), content, font_size=15, font_name="Helvetica", anchor="mm")
                curr_x += w
            y += h
            
        d_obj.rectangle([t_x1, y, t_x2, y+30], outline=border_color, width=1, fill=(240, 240, 240))
        curr_x = t_x1
        total_vals = ["Total", str(total_q), str(total_att), str(total_right), str(total_wrong), str(round(total_marks, 2))]
        for i, (w, text) in enumerate(zip(x_offsets, total_vals)):
            if i > 0:
                d_obj.line([curr_x, y, curr_x, y+30], fill=border_color, width=1)
            d_obj.text((curr_x + w//2, y+15), text, font_size=15, font_name="Helvetica-Bold", anchor="mm")
            curr_x += w
        y += 30
        
    y += 50 
    return y

def create_scorecard_pdf(data):
    width = 850
    banner_url = data.get("banner_url", "")
    banner_img, banner_size = get_image_size(banner_url)
    banner_h = 0
    if banner_img:
        b_w, b_h = banner_size
        banner_h = int((width / b_w) * b_h)
        
    content_h = draw_all(data, DryDraw(), width, banner_h, banner_img)
    final_h = max(1202, content_h)
    
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(width, final_h))
    
    # ---- ADD WATERMARK ----
    try:
        from PIL import Image
        wm = Image.open('icon.png').convert("RGBA")
        wm_w = int(width * 0.7) # 70% of width
        wm_h = int((wm_w / float(wm.width)) * wm.height)
        wm = wm.resize((wm_w, wm_h), Image.LANCZOS)
        
        alpha = wm.split()[3]
        alpha = alpha.point(lambda p: p * 0.04) # 4% opacity
        wm.putalpha(alpha)
        
        wm_io = io.BytesIO()
        wm.save(wm_io, format='PNG')
        wm_io.seek(0)
        
        from reportlab.lib.utils import ImageReader
        wm_ir = ImageReader(wm_io)
        paste_x = (width - wm_w) // 2
        paste_y = (final_h - wm_h) // 2
        
        c.drawImage(wm_ir, paste_x, paste_y, wm_w, wm_h, mask='auto')
    except Exception as e:
        pass
    # -----------------------
    
    real_draw = PDFDraw(c, final_h)
    draw_all(data, real_draw, width, banner_h, banner_img)
    
    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer
