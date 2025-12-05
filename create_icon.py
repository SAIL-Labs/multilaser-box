#!/usr/bin/env python3
"""
Script to generate application icons for Multi-Laser Controller
Creates a simple laser-themed icon with PyQt6 or PIL/Pillow
"""

import sys
import os

def create_icon_with_pil():
    """Create icon using PIL/Pillow"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create a high-resolution base image
        size = 1024
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle - dark blue/tech color
        margin = size // 10
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(30, 50, 100, 255),
            outline=(60, 100, 180, 255),
            width=size // 50
        )

        # Draw laser beams (red lines)
        center_x = size // 2
        center_y = size // 2
        beam_length = size // 3

        # Three laser beams at different angles
        angles = [-30, 0, 30]  # degrees
        import math

        for i, angle in enumerate(angles):
            rad = math.radians(angle)
            start_x = center_x - math.sin(rad) * beam_length // 2
            start_y = center_y - math.cos(rad) * beam_length // 2
            end_x = center_x + math.sin(rad) * beam_length // 2
            end_y = center_y + math.cos(rad) * beam_length // 2

            # Laser beam (red with glow effect)
            beam_width = size // 40
            # Glow
            draw.line(
                [(start_x, start_y), (end_x, end_y)],
                fill=(255, 100, 100, 180),
                width=beam_width * 2
            )
            # Core beam
            draw.line(
                [(start_x, start_y), (end_x, end_y)],
                fill=(255, 50, 50, 255),
                width=beam_width
            )

            # Laser dot at end
            dot_size = size // 20
            draw.ellipse(
                [end_x - dot_size, end_y - dot_size,
                 end_x + dot_size, end_y + dot_size],
                fill=(255, 0, 0, 255)
            )

        # Central control node
        node_size = size // 6
        draw.ellipse(
            [center_x - node_size, center_y - node_size,
             center_x + node_size, center_y + node_size],
            fill=(100, 150, 200, 255),
            outline=(200, 220, 255, 255),
            width=size // 80
        )

        # Inner circle detail
        node_inner = size // 10
        draw.ellipse(
            [center_x - node_inner, center_y - node_inner,
             center_x + node_inner, center_y + node_inner],
            fill=(150, 180, 220, 255)
        )

        # Save as PNG first
        png_path = 'figures/icon_source.png'
        img.save(png_path, 'PNG')
        print(f"✓ Created source PNG: {png_path}")

        # Create ICO for Windows (multiple sizes)
        ico_path = 'figures/icon.ico'
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, format='ICO', sizes=sizes)
        print(f"✓ Created Windows icon: {ico_path}")

        # For macOS ICNS, save individual sizes
        print("\nFor macOS .icns file, you have two options:")
        print("1. Use the online converter at https://cloudconvert.com/png-to-icns")
        print(f"   Upload: {png_path}")
        print("\n2. On macOS, use the following commands:")
        print("   mkdir -p MyIcon.iconset")

        iconset_sizes = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png"),
        ]

        # Try to create iconset directory and files
        try:
            os.makedirs('MyIcon.iconset', exist_ok=True)
            for size, filename in iconset_sizes:
                sized_img = img.resize((size, size), Image.Resampling.LANCZOS)
                sized_img.save(f'MyIcon.iconset/{filename}', 'PNG')
            print("\n   ✓ Created iconset files in MyIcon.iconset/")
            print("   Now run: iconutil -c icns MyIcon.iconset")
            print("   Then: mv MyIcon.icns figures/icon.icns")
        except Exception as e:
            print(f"\n   Note: Could not create iconset files: {e}")

        return True

    except ImportError:
        print("PIL/Pillow not installed. Install with: pip install Pillow")
        return False

def create_icon_with_pyqt():
    """Create icon using PyQt6"""
    try:
        from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QRadialGradient
        from PyQt6.QtCore import Qt, QPoint, QPointF

        size = 1024
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background circle
        margin = size // 10
        pen = QPen(QColor(60, 100, 180), size // 50)
        painter.setPen(pen)
        painter.setBrush(QColor(30, 50, 100))
        painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

        # Laser beams
        center = size // 2
        beam_length = size // 3

        import math
        angles = [-30, 0, 30]

        pen = QPen(QColor(255, 50, 50), size // 40)
        painter.setPen(pen)

        for angle in angles:
            rad = math.radians(angle)
            start_x = center - math.sin(rad) * beam_length // 2
            start_y = center - math.cos(rad) * beam_length // 2
            end_x = center + math.sin(rad) * beam_length // 2
            end_y = center + math.cos(rad) * beam_length // 2

            painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))

            # Dot at end
            dot_size = size // 20
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(QPointF(end_x, end_y), dot_size, dot_size)

        # Central node
        node_size = size // 6
        gradient = QRadialGradient(QPointF(center, center), node_size)
        gradient.setColorAt(0, QColor(150, 180, 220))
        gradient.setColorAt(1, QColor(100, 150, 200))

        painter.setBrush(gradient)
        pen = QPen(QColor(200, 220, 255), size // 80)
        painter.setPen(pen)
        painter.drawEllipse(center - node_size, center - node_size,
                           node_size * 2, node_size * 2)

        painter.end()

        # Save
        png_path = 'figures/icon_source.png'
        img.save(png_path)
        print(f"✓ Created source PNG: {png_path}")

        # Note: PyQt6 doesn't easily create .ico, recommend using PIL
        print("\nTo create .ico and .icns files:")
        print("Install Pillow: pip install Pillow")
        print("Then run this script again.")

        return True

    except ImportError:
        print("PyQt6 not installed.")
        return False

def main():
    """Main function to create icons"""
    print("Multi-Laser Controller - Icon Generator")
    print("=" * 50)

    # Ensure figures directory exists
    os.makedirs('figures', exist_ok=True)

    # Try PIL first (better for icon formats)
    success = create_icon_with_pil()

    if not success:
        print("\nTrying PyQt6 method...")
        success = create_icon_with_pyqt()

    if not success:
        print("\nCould not create icons with available libraries.")
        print("\nPlease install Pillow:")
        print("  pip install Pillow")
        print("\nOr use an online icon generator:")
        print("  https://www.favicon-generator.org/")
        print("  https://icon.kitchen/")
        return 1

    print("\n" + "=" * 50)
    print("Icon generation complete!")
    print("\nNext steps:")
    print("1. Check figures/icon_source.png to see the design")
    print("2. If you're on macOS and have iconutil, create .icns:")
    print("   iconutil -c icns MyIcon.iconset && mv MyIcon.icns figures/icon.icns")
    print("3. Commit the icons:")
    print("   git add figures/icon.ico figures/icon.icns")
    print("   git commit -m 'Add application icons'")

    return 0

if __name__ == '__main__':
    sys.exit(main())
