import io
import base64
from PIL import Image, ImageDraw, ImageFont
import os

def create_scorecard_image(data):
    width = 850
    sections = data.get("sections", [])
    num_sections = len(sections)
    
    # Create a canvas large enough, minimum 1202 (A4 height for 850 width)
    estimated_h = 1100 + (num_sections * 100)
    height = max(1202, estimated_h)
    
    img = Image.new('RGB', (width, int(height)), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        font_m = ImageFont.truetype("arial.ttf", 20) # साधारण टेक्स्ट साइज़ बढ़ा दिया
        font_b = ImageFont.truetype("arialbd.ttf", 20) # बोल्ड टेक्स्ट साइज़
        font_large = ImageFont.truetype("arialbd.ttf", 26) # बड़े हेडर का साइज़
        font_huge = ImageFont.truetype("arialbd.ttf", 34) # सबसे बड़े हेडर का साइज़
        font_s = ImageFont.truetype("arial.ttf", 17) # छोटे टेक्स्ट साइज़ (सेक्शन के अंदर)
        font_sb = ImageFont.truetype("arialbd.ttf", 17) # छोटे बोल्ड टेक्स्ट साइज़
    except:
        font_m = ImageFont.load_default()
        font_b = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_huge = ImageFont.load_default()
        font_s = ImageFont.load_default()
        font_sb = ImageFont.load_default()

    # Try fetching Banner
    banner_url = data.get("banner_url", "")
    banner_img = None
    if banner_url:
        try:
            import urllib.request
            req = urllib.request.Request(banner_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                b_data = response.read()
                temp_img = Image.open(io.BytesIO(b_data))
                banner_img = temp_img.convert("RGBA")
        except Exception as e:
            pass
            
    # Try fetching Candidate Photo
    photo_b64 = data.get("photo_b64", "")
    photo_url = data.get("photo_url", "")
    cand_photo = None
    
    if photo_b64:
        try:
            header, encoded = photo_b64.split(",", 1)
            photo_data = base64.b64decode(encoded)
            temp_img = Image.open(io.BytesIO(photo_data))
            cand_photo = temp_img.convert("RGBA")
        except Exception as e:
            pass
    elif photo_url:
        try:
            import urllib.request
            req = urllib.request.Request(photo_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                p_data = response.read()
                temp_img = Image.open(io.BytesIO(p_data))
                cand_photo = temp_img.convert("RGBA")
        except Exception as e:
            pass

    banner_h = 0
    if banner_img:
        b_w, b_h = banner_img.size
        # Limit banner height ratio if it's unreasonably tall
        banner_h = int((width / b_w) * b_h)
    
    # ---- ADD WATERMARK ----
    try:
        wm = Image.open('icon.png').convert("RGBA")
        wm_w = int(width * 0.7) # 70% of width
        wm_h = int((wm_w / float(wm.width)) * wm.height)
        wm = wm.resize((wm_w, wm_h), Image.LANCZOS)
        
        alpha = wm.split()[3]
        alpha = alpha.point(lambda p: p * 0.04) # 4% opacity
        wm.putalpha(alpha)
        
        # Center the watermark based on expected height
        paste_x = (width - wm_w) // 2
        
        # We'll center it vertically taking banner height into account
        est_y = banner_h + 900
        paste_y = (est_y - wm_h) // 2
        if paste_y < banner_h + 100: paste_y = banner_h + 100
        
        img.paste(wm, (paste_x, paste_y), wm)
    except Exception as e:
        pass
    # -----------------------

    d = ImageDraw.Draw(img)

    # HEADER
    top_box_y = 120
    if banner_img:
        b_w, b_h = banner_img.size
        new_h = int((width / b_w) * b_h)
        banner_img = banner_img.resize((width, new_h), Image.LANCZOS)
        
        bg = Image.new('RGB', (width, new_h), (255, 255, 255))
        bg.paste(banner_img, (0, 0), banner_img if banner_img.mode == 'RGBA' else None)
        img.paste(bg, (0, 50))
        
        top_box_y = new_h + 80
    else:
        # Fallback Title
        d.text((width//2, 40), "रेल भर्ती बोर्ड / RAILWAY RECRUITMENT BOARDS", fill="black", font=font_large, anchor="mm")
        d.text((width//2, 70), "CEN 01/2024 - ALP / सहायक लोको पायलट", fill="black", font=font_large, anchor="mm")
        top_box_y = 120

    # Table Top header box
    border_color = (0, 0, 0)
    top_box_x1 = 50
    top_box_x2 = width - 50

    exam_name = data.get("exam_name", "Test Score Card").upper()
    board_name = "RAILWAY RECRUITMENT BOARD" if "RRB" in exam_name else "EXAMINATION BOARD"
    if "SSC" in exam_name: board_name = "STAFF SELECTION COMMISSION"
    
    d.rectangle([top_box_x1, top_box_y, top_box_x2, top_box_y+30], outline=border_color, width=1)
    d.text((width//2, top_box_y+15), board_name, fill="black", font=font_m, anchor="mm")
    
    d.rectangle([top_box_x1, top_box_y+30, top_box_x2, top_box_y+60], outline=border_color, width=1)
    d.text((width//2, top_box_y+45), exam_name, fill="black", font=font_m, anchor="mm")

    # "Score Card" label
    d.text((width//2, top_box_y+85), "Candidate Score Card", fill="black", font=font_large, anchor="mm")

    # MAIN TABLE
    t_x1 = 50
    t_x2 = width - 50
    x_mid = 430
    y = top_box_y + 110

    import textwrap
    
    def draw_row(key, val, font_val=font_m, font_k=font_m):
        nonlocal y
        key_lines = textwrap.wrap(str(key), width=38)
        val_lines = textwrap.wrap(str(val), width=38)
        
        h = max(len(key_lines), len(val_lines)) * 26 + 10
        # Ensure minimum height of 40 like original tight spacing
        h = max(35, h)
        
        d.rectangle([t_x1, y, t_x2, y+h], outline=border_color, width=1)
        d.line([x_mid, y, x_mid, y+h], fill=border_color, width=1)
        
        center_row_y = y + h // 2
        
        tk_h = len(key_lines) * 26
        for idx, k in enumerate(key_lines):
            line_y = center_row_y - (tk_h // 2) + (idx * 26) + 13
            d.text((t_x1+10, line_y), k, fill="black", font=font_k, anchor="lm")
            
        tv_h = len(val_lines) * 26
        for idx, v in enumerate(val_lines):
            line_y = center_row_y - (tv_h // 2) + (idx * 26) + 13
            d.text((x_mid+10, line_y), v, fill="black", font=font_val, anchor="lm")
        
        y += h

    # Top Candidate Photo Row
    d.rectangle([t_x1, y, t_x2, y+100], outline=border_color, width=1)
    
    if cand_photo:
        pw, ph = cand_photo.size
        new_ph = 90
        new_pw = int((pw / ph) * new_ph)
        cand_photo = cand_photo.resize((new_pw, new_ph), Image.LANCZOS)
        
        pw_final, ph_final = cand_photo.size
        # Paste cand_photo centered in 100 height row
        img.paste(cand_photo, (t_x1 + 10, y + (100 - ph_final)//2), cand_photo if cand_photo.mode == 'RGBA' else None)
    else:
        # Fake a Silhouette avatar in the left space
        av_x, av_y = t_x1 + 30, y + 20
        d.ellipse([av_x, av_y, av_x+30, av_y+30], fill=(200, 200, 200))
        d.rectangle([av_x-15, av_y+30, av_x+45, av_y+80], fill=(200, 200, 200))
    
    y += 100

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
    draw_row(f"Total Raw Marks out of {overall_total}", score_str, font_k=font_b, font_val=font_b)

    if num_sections > 1:
        y += 15 # Add some gap before section analysis
        
        d.rectangle([t_x1, y, t_x2, y+30], outline=border_color, width=1, fill=(235, 235, 235))
        d.text((width//2, y+15), "Section Wise Details", fill="black", font=font_b, anchor="mm")
        y += 30
        
        # Grid Header
        d.rectangle([t_x1, y, t_x2, y+30], outline=border_color, width=1, fill=(245, 245, 245))
        # Total width = 750 (850 - 100). Split: 250, 90, 100, 105, 105, 100
        x_offsets = [250, 90, 100, 105, 105, 100]
        curr_x = t_x1
        headers = ["Section Name", "Total", "Attempt", "Right", "Wrong", "Marks"]
        
        for i, (w, text) in enumerate(zip(x_offsets, headers)):
            if i > 0:
                d.line([curr_x, y, curr_x, y+30], fill=border_color, width=1)
            d.text((curr_x + w//2, y+15), text, fill="black", font=font_sb, anchor="mm")
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
            
            import textwrap
            sec_lines = textwrap.wrap(sec_n, width=28)
            h = max(30, len(sec_lines)*16 + 10)
            
            vals = [sec_lines, str(s_tot), str(s_att), str(s_rt), str(s_wr), str(s_mk)]
            
            d.rectangle([t_x1, y, t_x2, y+h], outline=border_color, width=1)
            curr_x = t_x1
            for i, (w, content) in enumerate(zip(x_offsets, vals)):
                if i > 0:
                    d.line([curr_x, y, curr_x, y+h], fill=border_color, width=1)
                if i == 0:
                    # Draw wrapped text for section name
                    tk_h = len(content) * 16
                    center_row_y = y + h // 2
                    for line_idx, line in enumerate(content):
                        line_y = center_row_y - (tk_h // 2) + (line_idx * 16) + 8
                        d.text((curr_x + 6, line_y), line, fill="black", font=font_s, anchor="lm")
                else:
                    d.text((curr_x + w//2, y+h//2), content, fill="black", font=font_s, anchor="mm")
                curr_x += w
            y += h
            
        d.rectangle([t_x1, y, t_x2, y+30], outline=border_color, width=1, fill=(240, 240, 240))
        curr_x = t_x1
        total_vals = ["Total", str(total_q), str(total_att), str(total_right), str(total_wrong), str(round(total_marks, 2))]
        for i, (w, text) in enumerate(zip(x_offsets, total_vals)):
            if i > 0:
                d.line([curr_x, y, curr_x, y+30], fill=border_color, width=1)
            d.text((curr_x + w//2, y+15), text, fill="black", font=font_sb, anchor="mm")
            curr_x += w
        y += 30
            
    # Crop to final height, enforcing minimum A4 ratio height (1202)
    final_h = max(1202, y + 50)
    img = img.crop((0, 0, width, final_h))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr
