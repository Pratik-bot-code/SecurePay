import os
from PIL import Image, ImageDraw

def create_icon(size, is_maskable=False, is_round=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background
    if is_maskable:
        draw.rectangle([0, 0, size, size], fill=(10, 25, 47, 255))
    elif is_round:
        draw.ellipse([0, 0, size, size], fill=(10, 25, 47, 255))
    else:
        corner_radius = int(size * 0.22)
        draw.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=(10, 25, 47, 255))

    # Inner subtle glow border
    margin = int(size * 0.04)
    if is_round:
        draw.ellipse([margin, margin, size - margin, size - margin], outline=(0, 180, 216, 70), width=max(2, int(size * 0.015)))
    elif not is_maskable:
        inner_rad = int(size * 0.18)
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=inner_rad,
            outline=(0, 180, 216, 70),
            width=max(2, int(size * 0.015))
        )

    # Shield geometry
    scale = 0.58 if is_maskable or is_round else 0.65
    cx, cy = size // 2, size // 2
    sw = int(size * scale)
    sh = int(sw * 1.15)
    top = cy - int(sh * 0.48)
    left = cx - sw // 2
    right = cx + sw // 2
    mid_y = top + int(sh * 0.55)
    bottom = top + sh

    shield_pts = [
        (left, top + int(sh * 0.08)),
        (left + int(sw * 0.15), top),
        (cx, top + int(sh * 0.05)),
        (right - int(sw * 0.15), top),
        (right, top + int(sh * 0.08)),
        (right, mid_y),
        (cx, bottom),
        (left, mid_y)
    ]
    
    draw.polygon(shield_pts, fill=(15, 35, 65, 255), outline=(0, 180, 216, 255))

    chk_width = max(2, int(size * 0.055))
    chk_p1 = (cx - int(sw * 0.25), top + int(sh * 0.45))
    chk_p2 = (cx - int(sw * 0.05), top + int(sh * 0.65))
    chk_p3 = (cx + int(sw * 0.28), top + int(sh * 0.32))

    draw.line([chk_p1, chk_p2], fill=(45, 212, 191, 255), width=chk_width)
    draw.line([chk_p2, chk_p3], fill=(45, 212, 191, 255), width=chk_width)
    
    r = chk_width // 2
    for p in (chk_p1, chk_p2, chk_p3):
        draw.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=(45, 212, 191, 255))

    return img

def create_splash(width=480, height=800):
    img = Image.new("RGBA", (width, height), (10, 25, 47, 255))
    # Place a 180x180 icon in the center
    icon = create_icon(160)
    ix = (width - 160) // 2
    iy = (height - 160) // 2 - 40
    img.paste(icon, (ix, iy), icon)
    return img

def main():
    pwa_out = r"c:\Users\prati\OneDrive\Desktop\Secure Pay\frontend\public\icons"
    os.makedirs(pwa_out, exist_ok=True)

    # PWA icons
    create_icon(192).save(os.path.join(pwa_out, "icon-192.png"))
    create_icon(512).save(os.path.join(pwa_out, "icon-512.png"))
    create_icon(512, is_maskable=True).save(os.path.join(pwa_out, "icon-maskable-512.png"))
    create_icon(180).save(os.path.join(pwa_out, "apple-touch-icon.png"))
    fav32 = create_icon(32)
    fav32.save(os.path.join(pwa_out, "favicon-32x32.png"))
    fav32.save(r"c:\Users\prati\OneDrive\Desktop\Secure Pay\frontend\public\favicon.ico")

    # Android mipmaps
    res_dir = r"c:\Users\prati\OneDrive\Desktop\Secure Pay\frontend\android\app\src\main\res"
    density_map = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    for folder, size in density_map.items():
        folder_path = os.path.join(res_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        # Standard launcher icon
        create_icon(size).save(os.path.join(folder_path, "ic_launcher.png"))
        # Round launcher icon
        create_icon(size, is_round=True).save(os.path.join(folder_path, "ic_launcher_round.png"))
        # Foreground
        create_icon(size, is_maskable=True).save(os.path.join(folder_path, "ic_launcher_foreground.png"))

    # Splash screen
    splash = create_splash()
    splash.save(os.path.join(res_dir, "drawable", "splash.png"))

    print("PWA and Android icons generated successfully!")

if __name__ == "__main__":
    main()
