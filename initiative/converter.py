import json
import argparse
import math

def _get_modifier_text(score):
    """Calculates and returns the D&D 5e ability modifier text."""
    if not isinstance(score, (int, float)):
        return ''
    modifier = math.floor((score - 10) / 2)
    return f"({'+' if modifier >= 0 else ''}{modifier})"

def _generate_header_html(monster_data):
    """Generates the HTML for the monster header."""
    name = monster_data.get('name', 'Unnamed Monster')
    size = monster_data.get('size', 'Unknown')
    m_type = monster_data.get('type', 'creature')
    subtype = f" ({monster_data['subtype'].replace('any race', 'any race')})" if monster_data.get('subtype') else ''
    alignment = monster_data.get('alignment', 'unaligned')

    return f"""
<div class="mon-stat-block__header" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; line-height: 1.1; background-color: rgb(255, 255, 255);">
    <div class="mon-stat-block__name" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold; font-size: 34px; font-family: MrsEavesSmallCaps, Roboto, Helvetica, sans-serif; color: rgb(130, 32, 0);">
        <span class="mon-stat-block__name-link" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(130, 32, 0); text-decoration: none;">{name}</span>
    </div>
    <div class="mon-stat-block__meta" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-style: italic; margin-bottom: 15px;">{size} {m_type}{subtype}, {alignment}</div>
</div>
"""

def _generate_attributes_html(monster_data):
    """Generates the HTML for AC, HP, and Speed attributes."""
    hp_extra = f" ({monster_data.get('hit_dice', 'N/A')} + {monster_data.get('constitution',0) * 2})" if monster_data.get('hit_dice') else '' # Simple approximation if hit_dice is present.
    # Recalculate HP extra based on CON modifier and hit dice if available
    if monster_data.get('hit_dice') and monster_data.get('constitution'):
        try:
            num_dice = int(monster_data['hit_dice'].split('d')[0])
            con_mod = math.floor((int(monster_data['constitution']) - 10) / 2)
            hp_extra = f" ({monster_data['hit_dice']} + {num_dice * con_mod})"
        except ValueError:
            hp_extra = f" ({monster_data['hit_dice']})" # Fallback if parsing hit_dice fails
    else:
        hp_extra = ""


    return f"""
<div class="mon-stat-block__attributes" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Armor Class</span>&nbsp;<span class="mon-stat-block__attribute-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('armor_class', 'N/A')}&nbsp;</span><span class="mon-stat-block__attribute-data-extra" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">(natural armor)</span></span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Hit Points</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('hit_points', 'N/A')}&nbsp;</span><span class="mon-stat-block__attribute-data-extra" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{hp_extra}</span></span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Speed</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('speed', 'N/A')}</span>
    </div>
</div>
"""

def _generate_ability_scores_html(monster_data):
    """Generates the HTML for the ability scores block."""
    abilities_html = ""
    ability_order = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

    for stat in ability_order:
        score = monster_data.get(stat)
        mod_text = _get_modifier_text(score)
        stat_abbr = stat[:3].upper()
        
        abilities_html += f"""
<div class="ability-block__stat ability-block__stat--{stat_abbr.lower()}" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; width: 59.1667px; padding: 5px 0px; text-align: center;">
    <div class="ability-block__heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{stat_abbr}</div>
    <div class="ability-block__data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="ability-block__score" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{score}</span>&nbsp;<span class="ability-block__modifier" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-left: 2px;">{mod_text}</span></div>
</div>"""
    
    return f"""
<div class="mon-stat-block__stat-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: initial; border-color: initial; border-image: initial; min-height: 10px;"></div>
    <div class="ability-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex; flex-wrap: wrap; margin: 0px; color: rgb(130, 32, 0);">
        {abilities_html}
    </div>
</div>
"""

def _generate_tidbits_html(monster_data):
    """Generates HTML for saving throws, skills, senses, languages, and CR/PB."""
    tidbits_html = []

    # Saving Throws
    save_throws = []
    for stat in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
        save_key = f"{stat}_save"
        if monster_data.get(save_key) is not None and monster_data[save_key] != '':
            save_throws.append(f"{stat[:3].upper()} {monster_data[save_key]}")
    if save_throws:
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Saving Throws</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{', '.join(save_throws)}</span>
</div>""")

    # Skills
    skills = []
    for skill_key, value in monster_data.items():
        # Look for keys like "history": 12, "perception": 10 etc.
        if isinstance(value, (int, str)) and value != '' and skill_key not in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma', 'hit_points', 'armor_class', 'challenge_rating']:
            if '_save' not in skill_key and '_bonus' not in skill_key and '_dice' not in skill_key and 'hit_' not in skill_key:
                # Attempt to include common skills and values that might be present
                # This is a bit heuristic, as skill keys aren't consistently named e.g., 'history' vs 'stealth_skill'
                if any(s in skill_key for s in ['history', 'perception', 'stealth', 'insight', 'persuasion', 'medicine', 'religion', 'athletics', 'acrobatics', 'sleight_of_hand', 'arcana', 'investigation', 'nature', 'performance', 'intimidation', 'survival', 'deception', 'animal_handling']):
                    skill_name = skill_key.replace('_skill', '').replace('_', ' ').title()
                    skills.append(f"{skill_name} {value}")

    if skills:
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Skills</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{', '.join(skills)}</span>
</div>""")

    # Senses
    if monster_data.get('senses'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Senses</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['senses']}</span>
</div>""")

    # Languages
    if monster_data.get('languages'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Languages</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['languages']}</span>
</div>""")

    # Damage Vulnerabilities, Resistances, Immunities, Condition Immunities
    if monster_data.get('damage_vulnerabilities'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Damage Vulnerabilities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['damage_vulnerabilities']}</span>
</div>""")
    if monster_data.get('damage_resistances'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Damage Resistances</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['damage_resistances']}</span>
</div>""")
    if monster_data.get('damage_immunities'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Damage Immunities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['damage_immunities']}</span>
</div>""")
    if monster_data.get('condition_immunities'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Condition Immunities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['condition_immunities']}</span>
</div>""")


    # Challenge Rating and Proficiency Bonus
    cr = monster_data.get('challenge_rating', 'N/A')
    # Calculate proficiency bonus based on CR (simple approximation)
    try:
        if isinstance(cr, str) and '/' in cr:
            cr_val = float(eval(cr)) # Handles fractions like "1/4"
        else:
            cr_val = float(cr)
        pb = math.ceil(cr_val / 4) + 1 if cr_val > 0 else 2
        cr_display = f"{cr} (XP {int(cr_val * 200) if cr_val >= 1 else int(25/float(cr_val)) if cr_val != 0 else 10}; PB +{pb})"
    except (ValueError, TypeError, ZeroDivisionError):
        pb = 2 # Default for unparseable CRs or CR 0
        cr_display = f"{cr} (XP N/A; PB +{pb})"
    
    tidbits_html.append(f"""
<div class="mon-stat-block__tidbit-container" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex;">
    <div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Challenge</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{cr_display}</span>
    </div>
    <div class="mon-stat-block__tidbit-spacer" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; width: 40px; min-width: 10px;"></div>
    <div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Proficiency Bonus</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">+{pb}</span>
    </div>
</div>
""")

    return "\n".join(tidbits_html)

def _generate_description_block_html(heading_text, items):
    """Generates HTML for special abilities, actions, or legendary actions."""
    if not items:
        return ""

    content_html = ""
    for item in items:
        name = item.get('name', 'Unknown')
        desc = item.get('desc', 'No description.')
        
        # Replace newlines with <br> for HTML display if present
        desc = desc.replace('\\n', '<br>')

        # Attempt to find and format rollable elements from description, mimicking D&D Beyond's span with data attributes
        # This is a complex step, and this regex might not cover all cases but tries to get common patterns
        # For simplicity, we are *not* re-implementing the full rollable functionality or tooltips here,
        # but just keeping the numbers and formatting the text similarly.
        # Original: <span data-dicenotation="1d20+9" data-rolltype="to hit" data-rollaction="Tentacle" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">+9</span>
        # We will strip data attributes and hrefs, but try to keep text styling like bold/italic.

        # Heuristically format text that looks like dice notation or attack bonuses
        def replace_rollables(match):
            text = match.group(0)
            # Remove any existing <a> tags or complex span structures from the source desc
            text = text.replace('<a', '<span').replace('</a>', '</span>') # Replace <a> with <span> to remove links
            # Try to simplify existing span styles or data attributes for consistency
            text = re.sub(r'<span[^>]*data-[^>]*>', '', text) # Remove data attributes
            text = re.sub(r'<span[^>]*style="[^"]*"[^>]*>', '', text) # Remove inline styles from internal spans
            text = text.replace('</span>', '') # Remove closing span tags
            return text

        import re
        # This regex looks for patterns like "+NUM", "(XdY + Z)", "DC NUM", "NUM (XdY)"
        # It's a best effort to clean up potentially complex text.
        desc = re.sub(r'\+?\d+d\d+(\s*\+\s*\d+)?|\bDC\s*\d+|\d+\s*\((\d+d\d+\s*[\+\-]?\s*\d*)\)|\+?\d+(?=\s*to hit)', r'<span style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">\g<0></span>', desc)
        
        # Ensure <em> and <strong> tags are preserved or added where appropriate, based on typical D&D Beyond style
        # For example, ability names are usually bold and italic.
        if heading_text == "Traits":
             content_html += f"""<p style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;"><em style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><strong style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{name}.</strong></em>&nbsp;{desc}</p>"""
        else: # For Actions and Legendary Actions, name is usually bold, then desc follows.
            content_html += f"""<p style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;"><strong style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{name}.</strong>&nbsp;{desc}</p>"""
            
    return f"""
<div class="mon-stat-block__description-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
    <div class="mon-stat-block__description-block-heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-bottom-width: 1px; border-bottom-color: rgb(130, 32, 0); color: rgb(130, 32, 0); font-size: 24px; line-height: 1.4; margin-top: 20px; margin-bottom: 15px;">{heading_text}</div>
    <div class="mon-stat-block__description-block-content" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        {content_html}
    </div>
</div>
"""

def format_monster_notes(monster_data):
    """
    Formats various attributes of a monster into a comprehensive HTML string
    mimicking D&D Beyond stat block styling for the 'notes' field.
    All href links are removed.
    """
    html_parts = []

    # Overall container structure as per example
    html_parts.append(f"""<div class="mon-stat-block__header" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; line-height: 1.1; background-color: rgb(255, 255, 255);">
    <div class="mon-stat-block__name" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        <div class="name" style="">
            <h1 style="padding: 0px; font-variant-numeric: normal; font-variant-east-asian: normal; font-variant-caps: small-caps; font-variant-alternates: normal; font-variant-position: normal; font-variant-emoji: normal; letter-spacing: 1px; color: rgb(109, 0, 0); font-size: 1.8rem; line-height: 1; break-after: avoid; font-family: Georgia, &quot;Times New Roman&quot;, serif;">
                <div class="mon-stat-block__header" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; line-height: 1.1; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
                    <div class="mon-stat-block__name" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold; font-size: 34px; font-family: MrsEavesSmallCaps, Roboto, Helvetica, sans-serif; color: rgb(130, 32, 0);">
                        <span class="mon-stat-block__name-link" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(130, 32, 0); text-decoration: none;">{monster_data.get('name', 'Unnamed Monster')}</span>
                    </div>
                    <div class="mon-stat-block__meta" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-style: italic; margin-bottom: 15px;">{monster_data.get('size', 'Unknown')} {monster_data.get('type', 'creature')}{f' ({monster_data["subtype"]})' if monster_data.get('subtype') else ''}, {monster_data.get('alignment', 'unaligned')}</div>
                </div>
                <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: initial; border-color: initial; border-image: initial; min-height: 10px;"></div>
                <div class="mon-stat-block__attributes" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
                    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
                        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Armor Class</span>&nbsp;<span class="mon-stat-block__attribute-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('armor_class', 'N/A')}&nbsp;</span><span class="mon-stat-block__attribute-data-extra" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">(natural armor)</span></span>
                    </div>
                    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
                        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Hit Points</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('hit_points', 'N/A')}&nbsp;</span><span class="mon-stat-block__attribute-data-extra" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">({monster_data.get('hit_dice', 'N/A')})</span></span>
                    </div>
                    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
                        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Speed</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('speed', 'N/A')}</span>
                    </div>
                </div>
                <div class="mon-stat-block__stat-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
                    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: initial; border-color: initial; border-image: initial; min-height: 10px;"></div>
                    <div class="ability-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex; flex-wrap: wrap; margin: 0px; color: rgb(130, 32, 0);">
                        {_generate_ability_scores_html_for_main_block(monster_data)}
                    </div>
                    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: initial; border-color: initial; border-image: initial; min-height: 10px;"></div>
                </div>
                <div class="mon-stat-block__tidbits" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
                    {_generate_tidbits_html(monster_data)}
                </div>
                <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: initial; border-color: initial; border-image: initial; min-height: 10px;"></div>
                <div class="mon-stat-block__description-blocks" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-top: 20px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
                    {_generate_description_block_html("Traits", monster_data.get('special_abilities', []))}
                    {_generate_description_block_html("Actions", monster_data.get('actions', []))}
                    {_generate_description_block_html("Legendary Actions", monster_data.get('legendary_actions', []))}
                </div>
            </h1>
        </div>
    </div>
</div>""")

    return "".join(html_parts)

def _generate_ability_scores_html_for_main_block(monster_data):
    """
    Generates the HTML for the ability scores block,
    specifically for the main stat block HTML.
    """
    abilities_html = ""
    ability_order = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

    for stat in ability_order:
        score = monster_data.get(stat, 'N/A')
        mod_text = _get_modifier_text(score)
        stat_abbr = stat[:3].upper()
        
        abilities_html += f"""
<div class="ability-block__stat ability-block__stat--{stat_abbr.lower()}" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; width: 59.1667px; padding: 5px 0px; text-align: center;">
    <div class="ability-block__heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{stat_abbr}</div>
    <div class="ability-block__data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="ability-block__score" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{score}</span>&nbsp;<span class="ability-block__modifier" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-left: 2px;">{mod_text}</span></div>
</div>"""
    return abilities_html


def convert_monster_data(input_json_path, output_json_path):
    """
    Reads monster data from a JSON file and converts it to the Initiative Tracker format.
    """
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            monster_dump_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_json_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_json_path}. Please ensure it's valid JSON.")
        return

    converted_monsters = []
    for monster in monster_dump_data:
        try:
            # Ensure HP is an integer for totalHp
            hp_value = int(monster.get('hit_points', 0))
            
            # Determine bgColor based on monster type for visual distinction
            # This is a placeholder; you might want a more sophisticated mapping
            bg_color = "bg-gray-200" # Default color
            if "dragon" in monster.get('type', '').lower():
                bg_color = "bg-red-500"
            elif "aberration" in monster.get('type', '').lower():
                bg_color = "bg-purple-500"
            elif "humanoid" in monster.get('type', '').lower():
                bg_color = "bg-green-500"
            elif "undead" in monster.get('type', '').lower():
                bg_color = "bg-zinc-700"
            elif "beast" in monster.get('type', '').lower():
                bg_color = "bg-yellow-500"
            elif "fiend" in monster.get('type', '').lower():
                bg_color = "bg-red-900"


            converted_monster = {
                "name": monster.get('name', 'Unnamed Monster'),
                "hp": str(hp_value),
                "totalHp": str(hp_value),
                "statuses": [],
                "bgColor": bg_color,
                "bgImageKey": "", # No image URLs from dump
                "notes": format_monster_notes(monster) # This now generates the full HTML string
            }
            converted_monsters.append(converted_monster)
        except Exception as e:
            print(f"Warning: Failed to process monster '{monster.get('name', 'Unknown')}' due to: {e}")
            continue

    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(converted_monsters, f, indent=2, ensure_ascii=False)
        print(f"Successfully converted {len(converted_monsters)} monsters to {output_json_path}")
    except IOError as e:
        print(f"Error writing to output file {output_json_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert D&D monster data from a dump to Initiative Tracker format.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON monster dump file.")
    parser.add_argument("output_file", type=str, help="Path for the output JSON file in Initiative Tracker format.")
    
    args = parser.parse_args()
    
    convert_monster_data(args.input_file, args.output_file)

