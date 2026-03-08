import os

templates_dir = r"c:\Users\suppo\OneDrive\Desktop\careerjet\app\resumes\templates"
os.makedirs(templates_dir, exist_ok=True)

# Archetypes
MODERN_STYLE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Helvetica', sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0.5in; }
        .header { border-bottom: 2px solid {{ accent_color }}; padding-bottom: 20px; margin-bottom: 30px; text-align: center; }
        .header h1 { font-size: 28pt; margin: 0; color: #111; text-transform: uppercase; }
        .header .title { font-size: 14pt; color: {{ accent_color }}; font-weight: bold; }
        .section-title { font-size: 12pt; font-weight: 800; color: {{ accent_color }}; text-transform: uppercase; margin-top: 25px; border-bottom: 1px solid #eee; }
        .item { margin-bottom: 15px; }
        .item-header { display: flex; justify-content: space-between; font-weight: bold; }
        .skills { display: flex; flex-wrap: wrap; gap: 8px; }
        .skill { background: #f0f0f0; padding: 4px 10px; border-radius: 4px; font-size: 9pt; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ header.full_name }}</h1>
        <div class="title">{{ header.title }}</div>
        <div>{{ header.email }} | {{ header.phone }} | {{ header.location }}</div>
    </div>
    <div class="section"><h2 class="section-title">Summary</h2><p>{{ summary }}</p></div>
    <div class="section"><h2 class="section-title">Experience</h2>
        {% for exp in experience %}<div class="item">
            <div class="item-header"><span>{{ exp.role }}</span><span>{{ exp.duration }}</span></div>
            <div style="color: {{ accent_color }};">{{ exp.company }}</div>
            <ul>{% for a in exp.achievements %}<li>{{ a }}</li>{% endfor %}</ul>
        </div>{% endfor %}
    </div>
    <div class="section"><h2 class="section-title">Skills</h2><div class="skills">
        {% for s in skills %}<span class="skill">{{ s }}</span>{% endfor %}
    </div></div>
</body>
</html>
"""

SIDEBAR_STYLE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; display: flex; min-height: 100vh; }
        .sidebar { width: 30%; background: {{ accent_color }}; color: white; padding: 40px 20px; }
        .main { width: 70%; padding: 40px; background: white; }
        .sidebar h1 { font-size: 22pt; margin-bottom: 5px; }
        .sidebar-section { margin-top: 30px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px; }
        .section-title { font-size: 14pt; font-weight: bold; color: {{ accent_color }}; border-bottom: 2px solid {{ accent_color }}; margin-top: 30px; }
        .item { margin-bottom: 20px; }
        .skill { display: inline-block; background: rgba(255,255,255,0.2); padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 9pt; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h1>{{ header.full_name }}</h1>
        <p>{{ header.title }}</p>
        <div class="sidebar-section">
            <p>{{ header.email }}</p><p>{{ header.phone }}</p><p>{{ header.location }}</p>
        </div>
        <div class="sidebar-section">
            <h3>Skills</h3>
            {% for s in skills %}<span class="skill">{{ s }}</span>{% endfor %}
        </div>
    </div>
    <div class="main">
        <div class="section"><h2 class="section-title">Profile</h2><p>{{ summary }}</p></div>
        <div class="section"><h2 class="section-title">Experience</h2>
            {% for exp in experience %}<div class="item">
                <div style="display:flex; justify-content:space-between"><strong>{{ exp.role }}</strong><span>{{ exp.duration }}</span></div>
                <div style="font-style:italic">{{ exp.company }}</div>
                <ul>{% for a in exp.achievements %}<li>{{ a }}</li>{% endfor %}</ul>
            </div>{% endfor %}
        </div>
    </div>
</body>
</html>
"""

DARK_STYLE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Courier New', monospace; background: #1a1a1a; color: #eee; padding: 40px; }
        .header { border-left: 5px solid {{ accent_color }}; padding-left: 20px; margin-bottom: 40px; }
        .header h1 { font-size: 30pt; color: white; margin: 0; }
        .section-title { color: {{ accent_color }}; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #333; }
        .item { margin-bottom: 20px; border-bottom: 1px solid #222; padding-bottom: 10px; }
        .skill { border: 1px solid {{ accent_color }}; padding: 2px 8px; color: {{ accent_color }}; margin: 3px; display: inline-block; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ header.full_name }}</h1>
        <div style="color: {{ accent_color }}; font-weight: bold;">{{ header.title }}</div>
        <div style="font-size: 9pt; opacity: 0.7;">{{ header.email }} | {{ header.phone }} | {{ header.location }}</div>
    </div>
    <div class="section"><h2 class="section-title">> Summary</h2><p>{{ summary }}</p></div>
    <div class="section"><h2 class="section-title">> Experience</h2>
        {% for exp in experience %}<div class="item">
            <div style="display:flex; justify-content:space-between"><strong>{{ exp.role }}</strong><span>{{ exp.duration }}</span></div>
            <div style="color: {{ accent_color }}">{{ exp.company }}</div>
            {% for a in exp.achievements %}<div>- {{ a }}</div>{% endfor %}
        </div>{% endfor %}
    </div>
</body>
</html>
"""

configs = {
    # Original 50
    "modern": (MODERN_STYLE, "#4f46e5"), "executive": (MODERN_STYLE, "#b8860b"), "creative": (SIDEBAR_STYLE, "#2d3436"), "academic": (MODERN_STYLE, "#333"), "minimal": (MODERN_STYLE, "#999"),
    "sleek": (MODERN_STYLE, "#3b82f6"), "bold": (MODERN_STYLE, "#000"), "impact": (MODERN_STYLE, "#ff4757"), "corporate": (MODERN_STYLE, "#000"), "midnight": (DARK_STYLE, "#3b82f6"),
    "ruby": (MODERN_STYLE, "#b33939"), "emerald": (MODERN_STYLE, "#059669"), "indigo": (SIDEBAR_STYLE, "#4338ca"), "sunset": (SIDEBAR_STYLE, "#ef4444"), "clean": (MODERN_STYLE, "#10b981"),
    "compact": (MODERN_STYLE, "#000"), "elegant": (MODERN_STYLE, "#1e293b"), "startup": (MODERN_STYLE, "#ff4757"), "classic": (MODERN_STYLE, "#000"), "modern_dark": (DARK_STYLE, "#60a5fa"),
    "duotone_purple": (MODERN_STYLE, "#9333ea"), "sage_garden": (MODERN_STYLE, "#708238"), "social_pro": (SIDEBAR_STYLE, "#1da1f2"), "geometric": (MODERN_STYLE, "#f43f5e"), "cream_peach": (SIDEBAR_STYLE, "#fb923c"),
    "spectrum": (MODERN_STYLE, "#3b82f6"), "clarity": (MODERN_STYLE, "#0ea5e9"), "spacesmart": (MODERN_STYLE, "#64748b"), "polished_path": (MODERN_STYLE, "#1e293b"), "flexform": (MODERN_STYLE, "#4d7c0f"),
    "nextstep": (MODERN_STYLE, "#b91c1c"), "turquoise_corp": (MODERN_STYLE, "#0d9488"), "scholar_line": (MODERN_STYLE, "#3f3f46"), "collage": (SIDEBAR_STYLE, "#db2777"), "swiss": (MODERN_STYLE, "#dc2626"),
    "data_expert": (MODERN_STYLE, "#2563eb"), "terminal": (DARK_STYLE, "#22c55e"), "lavender": (SIDEBAR_STYLE, "#8b5cf6"), "luxury_gold": (MODERN_STYLE, "#d4af37"), "silver_lining": (MODERN_STYLE, "#94a3b8"),
    "navy_seal": (MODERN_STYLE, "#1e3a8a"), "mint_fresh": (MODERN_STYLE, "#2dd4bf"), "peach_dev": (MODERN_STYLE, "#fb923c"), "autumn": (MODERN_STYLE, "#92400e"), "sky_gradient": (SIDEBAR_STYLE, "#0ea5e9"),
    "charcoal_bold": (MODERN_STYLE, "#171717"), "minimal_ink": (MODERN_STYLE, "#000000"), "classic_journal": (MODERN_STYLE, "#000000"), "legal_brief": (MODERN_STYLE, "#1e293b"), "portfolio_plus": (SIDEBAR_STYLE, "#4338ca"),
    # New 50+
    "careeredge": (SIDEBAR_STYLE, "#b91c1c"), "pureelegance": (MODERN_STYLE, "#d1d5db"), "profileprime": (MODERN_STYLE, "#1e40af"), "readease": (MODERN_STYLE, "#0f172a"),
    "multipro": (MODERN_STYLE, "#374151"), "personaprint": (SIDEBAR_STYLE, "#7c3aed"), "standout": (SIDEBAR_STYLE, "#db2777"), "probanner": (SIDEBAR_STYLE, "#2563eb"),
    "blendform": (MODERN_STYLE, "#4b5563"), "clearline": (MODERN_STYLE, "#06b6d4"), "designmark": (MODERN_STYLE, "#f97316"), "focusform": (MODERN_STYLE, "#111827"),
    "atspro": (MODERN_STYLE, "#000000"), "streamline": (SIDEBAR_STYLE, "#059669"), "claritypro": (SIDEBAR_STYLE, "#0ea5e9"), "inspireform": (MODERN_STYLE, "#ea580c"),
    "artistry": (MODERN_STYLE, "#8b5cf6"), "sharplines": (MODERN_STYLE, "#0f172a"), "designslate": (DARK_STYLE, "#475569"), "contentfocus": (MODERN_STYLE, "#1e293b"),
    "nursing_pro": (MODERN_STYLE, "#0891b2"), "legal_expert": (MODERN_STYLE, "#1e1b4b"), "sales_giant": (MODERN_STYLE, "#b91c1c"), "dev_mono": (DARK_STYLE, "#10b981"),
    "hr_harmonious": (SIDEBAR_STYLE, "#ec4899"), "retail_star": (MODERN_STYLE, "#f59e0b"), "chef_cuisine": (MODERN_STYLE, "#1e293b"), "real_estate": (SIDEBAR_STYLE, "#1d4ed8"),
    "fitness_coach": (SIDEBAR_STYLE, "#dc2626"), "travel_guide": (SIDEBAR_STYLE, "#0369a1"), "hush_minimal": (MODERN_STYLE, "#94a3b8"), "stark_white": (MODERN_STYLE, "#000000"),
    "zen_master": (MODERN_STYLE, "#1e293b"), "grid_logic": (MODERN_STYLE, "#4b5563"), "editorial": (MODERN_STYLE, "#000000"), "vintage_type": (MODERN_STYLE, "#44403c"),
    "futuro": (MODERN_STYLE, "#7c3aed"), "soft_focus": (MODERN_STYLE, "#f472b6"), "bold_box": (MODERN_STYLE, "#000000"), "the_minimal": (MODERN_STYLE, "#6b7280"),
    "impact_plus": (MODERN_STYLE, "#ef4444"), "clean_pro": (MODERN_STYLE, "#1e293b"), "modern_edge": (MODERN_STYLE, "#3b82f6"), "classic_serif": (MODERN_STYLE, "#1e1b4b"),
    "modern_grid": (MODERN_STYLE, "#0f172a"), "sidebar_pro": (SIDEBAR_STYLE, "#1e293b"), "content_king": (MODERN_STYLE, "#111827"), "value_prop": (MODERN_STYLE, "#4338ca"),
    "career_map": (SIDEBAR_STYLE, "#10b981"), "the_standard": (MODERN_STYLE, "#1e293b"),
}

for t_id, (style, color) in configs.items():
    file_path = os.path.join(templates_dir, f"{t_id}.jinja")
    content = style.replace("{{ accent_color }}", color)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Successfully generated {len(configs)} templates.")
