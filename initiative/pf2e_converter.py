import json
import argparse
import math
import os
import re
from bs4 import BeautifulSoup

# Removed: _get_ability_score_from_mod as it's no longer needed for pseudo D&D stats

def _format_pf2_senses(senses_list):
    """Formats PF2e senses list into a readable string."""
    if not senses_list:
        return "None"
    
    formatted_senses = []
    for sense in senses_list:
        s_type = sense.get('type', 'unknown')
        s_acuity = sense.get('acuity', '')
        s_range = sense.get('range', '')

        part = s_type.replace('-', ' ').title()
        if s_acuity:
            part = f"{s_acuity.title()} {part}"
        if s_range:
            part += f" {s_range} feet"
        formatted_senses.append(part)
    return ", ".join(formatted_senses)

def _format_pf2_dr_immunities(dr_list):
    """Formats PF2e damage/resistance/immunity lists into a readable string."""
    if not dr_list:
        return "None"
    formatted = []
    for item in dr_list:
        item_type = item.get('type', 'unknown').replace('-', ' ').title()
        item_value = item.get('value', '')
        formatted.append(f"{item_type} {item_value}" if item_value else item_type)
    return ", ".join(formatted)

def _format_pf2_condition_immunities(ci_list):
    """Formats PF2e condition immunity lists into a readable string."""
    if not ci_list:
        return "None"
    formatted = [item.replace('-', ' ').title() for item in ci_list]
    return ", ".join(formatted)

def _get_action_cost_symbol(action_type, actions_value):
    """Returns the visual symbol for PF2e action costs."""
    if action_type == 'action':
        if actions_value == 1: return '[A]'
        if actions_value == 2: return '[AA]'
        if actions_value == 3: return '[AAA]'
        return f"[{actions_value}A]" # Fallback for unexpected number
    elif action_type == 'reaction': return '[R]'
    elif action_type == 'free': return '[F]'
    elif action_type == 'passive': return '[P]' # Passive abilities often have no symbol or a special one
    return ''


def _generate_header_html(monster_data):
    """Generates the HTML for the monster header."""
    name = monster_data.get('name', 'Unnamed Monster')
    
    # Size
    size_trait = monster_data['system']['traits'].get('size', {}).get('value', 'M') # Get size safely
    pf2_size_map = {
        'tiny': 'Tiny', 'sm': 'Small', 'med': 'Medium', 'lg': 'Large',
        'huge': 'Huge', 'grg': 'Gargantuan'
    }
    size_display = pf2_size_map.get(size_trait, 'Unknown')

    # Rarity
    rarity = monster_data['system']['traits'].get('rarity', 'common')
    rarity_display = rarity.title() if rarity != 'common' else ''

    # Alignment (safe access and inference)
    alignment_value = monster_data.get('system', {}).get('details', {}).get('alignment', {}).get('value')
    
    if alignment_value:
        alignment_display = alignment_value.replace('-', ' ').title()
    else:
        # Infer alignment from traits.value
        traits = monster_data['system']['traits'].get('value', [])
        is_lawful = 'lawful' in traits
        is_chaotic = 'chaotic' in traits
        is_good = 'good' in traits
        is_evil = 'evil' in traits

        horizontal = ""
        if is_lawful: horizontal = "Lawful"
        elif is_chaotic: horizontal = "Chaotic"
        
        vertical = ""
        if is_good: vertical = "Good"
        elif is_evil: vertical = "Evil"

        if horizontal and vertical:
            alignment_display = f"{horizontal} {vertical}"
        elif horizontal:
            alignment_display = f"{horizontal} Neutral"
        elif vertical:
            alignment_display = f"Neutral {vertical}"
        else:
            alignment_display = "Unaligned" # Default if no specific alignment traits


    # Creature Type / Traits (now including all non-filtered traits)
    all_traits = monster_data['system']['traits'].get('value', [])
    
    # Define sets of known PF2e trait categories for filtering from the meta line
    pf2_alignment_traits = {'chaotic', 'evil', 'good', 'lawful', 'neutral', 'unaligned'}
    pf2_rarity_traits = {'common', 'rare', 'uncommon', 'unique'}
    
    meta_traits_list = []

    # Add rarity if applicable
    if rarity_display and rarity_display.lower() != 'common':
        meta_traits_list.append(rarity_display)
    
    # Add size
    meta_traits_list.append(size_display)

    # Add primary creature type from system.details.creatureType if present
    main_creature_type_from_details = monster_data['system']['details'].get('creatureType', '').lower()
    if main_creature_type_from_details and main_creature_type_from_details not in [p.lower() for p in meta_traits_list]:
        meta_traits_list.append(main_creature_type_from_details.title())
    
    # Add all other traits, excluding only alignment and rarity traits, and already added main type
    for trait in sorted(all_traits): # Sort traits for consistent ordering
        trait_lower = trait.lower()
        
        if trait_lower in pf2_alignment_traits or \
           trait_lower in pf2_rarity_traits or \
           trait_lower == main_creature_type_from_details:
            continue
            
        # No special handling for "Fiend (Demon)" pattern; just add "Fiend" and "Demon" separately if they exist
        
        # Add other traits, ensuring they haven't been added yet (case-insensitive check)
        if trait.title() not in [x.title() for x in meta_traits_list]: # Case-insensitive check for duplication
            meta_traits_list.append(trait.title())

    # Ensure uniqueness and sort additional descriptors
    final_ordered_meta_parts = []
    seen = set()
    for item in meta_traits_list:
        # Check against lowercased version to handle case-insensitivity for duplicates
        if item.lower() not in seen:
            final_ordered_meta_parts.append(item)
            seen.add(item.lower())

    # Final string assembly for the meta line
    final_meta_string = " ".join(final_ordered_meta_parts)
    
    if alignment_display and alignment_display != "Unaligned": # Only append if not already 'Unaligned' or if there are other parts
        if final_meta_string:
            final_meta_string += ", " + alignment_display
        else:
            final_meta_string = alignment_display 
    
    if not final_meta_string: # Final fallback
        final_meta_string = "Unaligned"


    return f"""
<div class="mon-stat-block__header" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; line-height: 1.1; background-color: rgb(255, 255, 255);">
    <div class="mon-stat-block__name" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold; font-size: 34px; font-family: MrsEavesSmallCaps, Roboto, Helvetica, sans-serif; color: rgb(0, 0, 0);">
        <span class="mon-stat-block__name-link" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); text-decoration: none;">{name}</span>
    </div>
    <div class="mon-stat-block__meta" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-style: italic; margin-bottom: 15px;">{final_meta_string}</div>
</div>
"""

def _generate_attributes_html(monster_data):
    """Generates the HTML for AC, HP, and Speed attributes."""
    
    # AC details
    ac_value = monster_data['system']['attributes']['ac'].get('value', 'N/A')
    ac_details = monster_data['system']['attributes']['ac'].get('details', '')
    ac_display = f"{ac_value} ({ac_details})" if ac_details else str(ac_value)

    # HP details
    hp_max = monster_data['system']['attributes']['hp'].get('max', 'N/A')
    hp_details = monster_data['system']['attributes']['hp'].get('details', '') # Often contains hit dice
    hp_display = f"{hp_max} {hp_details}" if hp_details else str(hp_max)

    # Speed details
    speed_value = monster_data['system']['attributes']['speed'].get('value', 'N/A')
    other_speeds = []
    if monster_data['system']['attributes']['speed'].get('otherSpeeds'):
        for s in monster_data['system']['attributes']['speed']['otherSpeeds']:
            s_type = s.get('type', 'unknown').replace('-', ' ')
            s_value = s.get('value', 'N/A')
            other_speeds.append(f"{s_type} {s_value} ft.")
    
    speed_display = f"{speed_value} ft."
    if other_speeds:
        speed_display += ", " + ", ".join(other_speeds)

    # Perception details
    perception_mod = monster_data['system']['perception'].get('mod', 0)
    perception_senses = _format_pf2_senses(monster_data['system']['perception'].get('senses', []))
    perception_display = f"+{perception_mod}" if perception_mod >= 0 else str(perception_mod) # Format as +X or -X
    if perception_senses and perception_senses != "None":
        perception_display += f"; {perception_senses}"


    return f"""
<div class="mon-stat-block__attributes" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 14px; font-variant-caps: normal; letter-spacing: normal;">
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Armor Class</span>&nbsp;<span class="mon-stat-block__attribute-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{ac_display}&nbsp;</span></span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Hit Points</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{hp_display}</span></span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Perception</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{perception_display}</span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Speed</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{speed_display}</span>
    </div>
</div>
"""

def _generate_ability_scores_html_for_main_block(monster_data):
    """
    Generates the HTML for the ability scores block using PF2e modifiers.
    """
    abilities_html = ""
    ability_order = ['str', 'dex', 'con', 'int', 'wis', 'cha'] # PF2e uses abbreviations

    for stat_abbr in ability_order:
        mod = monster_data['system']['abilities'].get(stat_abbr, {}).get('mod')
        mod_text = f"({'+' if mod >= 0 else ''}{mod})" if mod is not None else 'N/A' # Display only modifier
        
        abilities_html += f"""
<div class="ability-block__stat ability-block__stat--{stat_abbr}" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; width: 59.1667px; padding: 5px 0px; text-align: center;">
    <div class="ability-block__heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{stat_abbr.upper()}</div>
    <div class="ability-block__data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="ability-block__modifier" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{mod_text}</span></div>
</div>"""
    return abilities_html


def _generate_tidbits_html(monster_data):
    """Generates HTML for saving throws, skills, senses, languages, and CR/PB."""
    tidbits_html = []

    # Saving Throws
    save_throws = []
    # PF2e saves are fortitude, reflex, will
    for save_type in ['fortitude', 'reflex', 'will']:
        save_value = monster_data['system']['saves'].get(save_type, {}).get('value')
        if save_value is not None:
            save_throws.append(f"{save_type.title()} {save_value}")
    if save_throws:
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Saving Throws</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{', '.join(save_throws)}</span>
</div>""")

    # Skills
    skills_list = []
    if monster_data['system'].get('skills'):
        for skill_name, skill_data in monster_data['system']['skills'].items():
            if skill_data.get('base') is not None:
                skills_list.append(f"{skill_name.title()} {skill_data['base']}")
    if skills_list:
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Skills</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{', '.join(skills_list)}</span>
</div>""")

    # Languages
    languages_details = monster_data['system']['details']['languages'].get('details')
    languages_value = monster_data['system']['details']['languages'].get('value', [])
    if languages_details:
        languages_display = languages_details
    elif languages_value:
        languages_display = ", ".join([lang.title() for lang in languages_value])
    else:
        languages_display = "None"
    
    if languages_display != "None":
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Languages</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{languages_display}</span>
</div>""")

    # Weaknesses, Resistances, Immunities (from system.attributes)
    weaknesses = _format_pf2_dr_immunities(monster_data['system']['attributes'].get('weaknesses', []))
    if weaknesses != "None":
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Weaknesses</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{weaknesses}</span>
</div>""")
    
    resistances = _format_pf2_dr_immunities(monster_data['system']['attributes'].get('resistances', []))
    if resistances != "None":
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Resistances</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{resistances}</span>
</div>""")

    immunities = _format_pf2_dr_immunities(monster_data['system']['attributes'].get('immunities', []))
    if immunities != "None":
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Immunities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{immunities}</span>
</div>""")
        
    condition_immunities_list = monster_data['system']['attributes'].get('conditionImmunities', [])
    if condition_immunities_list:
        condition_immunities_display = _format_pf2_condition_immunities(condition_immunities_list)
        if condition_immunities_display != "None":
            tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Condition Immunities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{condition_immunities_display}</span>
</div>""")

    # Challenge Rating (Level in PF2e)
    level = monster_data['system']['details'].get('level', {}).get('value', 'N/A')
    
    tidbits_html.append(f"""
<div class="mon-stat-block__tidbit-container" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex;">
    <div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(0, 0, 0); line-height: 1.2;">
        <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Level</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{level}</span>
    </div>
</div>
""")

    return "\n".join(tidbits_html)


def _clean_description_html(description_value):
    """
    Cleans description HTML by removing specific PF2e UUIDs and tags,
    and ensuring newlines are br tags.
    """
    if not description_value:
        return ""
    
    # Pattern to capture UUIDs that have display text in curly braces
    # e.g., @UUID[Compendium.pf2e.conditionitems.Item.Grabbed]{Grabbed} -> Grabbed
    cleaned_desc = re.sub(r'@UUID\[[^\]]+\]\{([^}]+)\}', r'\1', description_value)
    
    # Pattern to capture UUIDs that don't have curly braces, taking the last part of the path
    # e.g., @UUID[Compendium.pf2e.conditionitems.Item.Grabbed] -> Grabbed
    # This regex is more specific: it looks for @UUID[...] and captures the segment after the last '.' or '/'
    # Updated regex to handle different path separators if necessary, and ensure only the name is captured
    cleaned_desc = re.sub(r'@UUID\[(?:[^\]]*[/\.])?([^\].]+?)\]', r'\1', cleaned_desc)


    cleaned_desc = re.sub(r'@Check\[([^\]]+)\]', lambda m: f"Check ({m.group(1).replace('|', ' ').title()})", cleaned_desc)
    cleaned_desc = re.sub(r'@Damage\[([^\]]+)\]', lambda m: f"{m.group(1).replace('[', ' ').replace(']', ' ')} damage", cleaned_desc)
    cleaned_desc = re.sub(r'@Localize\[[^\]]+\]', '', cleaned_desc) # Remove localize tags
    cleaned_desc = re.sub(r'\[\[/r ([^\]]+)\]\]', r'(\1)', cleaned_desc) # Replace [[/r 2d6]] with (2d6)
    cleaned_desc = re.sub(r'\[\[/br (.*?)\]\]', r'(\1)', cleaned_desc) # Replace [[/br ...]] with (...)

    # Replace newlines with <br> for HTML display
    cleaned_desc = cleaned_desc.replace('\n', '<br>')

    # Use BeautifulSoup to parse and clean any remaining HTML tags or hrefs
    soup = BeautifulSoup(cleaned_desc, 'html.parser')
    for a_tag in soup.find_all('a'):
        a_tag.unwrap() # Remove the <a> tag but keep its content

    return str(soup).strip()


def _generate_description_block_html(heading_text, items):
    """Generates HTML for special abilities, actions, or legendary actions."""
    if not items:
        return ""

    content_html = ""
    for item in items:
        name = item.get('name', 'Unknown')
        desc = item.get('system', {}).get('description', {}).get('value', 'No description.')
        action_type = item.get('system', {}).get('actionType', {}).get('value')
        actions_value = item.get('system', {}).get('actions', {}).get('value')

        cleaned_desc = _clean_description_html(desc)
        
        # Add action cost symbol for actions/reactions/free actions
        action_symbol = _get_action_cost_symbol(action_type, actions_value)
        if action_symbol and action_symbol != '[P]': # Don't add symbol for passives here, they usually just have bold name
            name_display = f"{name} {action_symbol}"
        else:
            name_display = name

        # PF2e specific formatting for Strikes (Melee/Ranged items)
        if item.get('type') == 'melee': # Also covers ranged strikes disguised as 'melee' type
            bonus = item['system']['bonus'].get('value', 'N/A')
            damage_rolls = item['system'].get('damageRolls', {})
            
            damage_parts = []
            for d_key in sorted(damage_rolls.keys()):
                d_roll = damage_rolls[d_key]
                damage = d_roll.get('damage', 'N/A')
                d_type = d_roll.get('damageType', 'physical').title()
                damage_parts.append(f"{damage} {d_type} damage")
            
            damage_display = ", ".join(damage_parts)
            
            # Extract reach from traits
            reach_trait = next((t for t in item['system']['traits'].get('value', []) if 'reach-' in t), None)
            reach_display = reach_trait.replace('reach-', 'reach ').replace('-', ' ') + "," if reach_trait else ""

            # Extract thrown range from traits for ranged strikes
            thrown_trait = next((t for t in item['system']['traits'].get('value', []) if 'thrown-' in t), None)
            thrown_range_display = thrown_trait.replace('thrown-', 'range increment ') + ' ft.' if thrown_trait else ""

            # Determine if it's a ranged or melee attack
            weapon_type = item['system'].get('weaponType', {}).get('value', 'melee')
            is_ranged_trait = any('range-' in t for t in item['system']['traits'].get('value', [])) or \
                   any('thrown-' in t for t in item['system']['traits'].get('value', []))
            attack_type_display = "Ranged Attack" if weapon_type == 'ranged' or is_ranged_trait else "Melee Attack"

            strike_line = f"<strong style=\"box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;\">{name_display}.</strong> {attack_type_display}: +{bonus} to hit, "
            if reach_display:
                strike_line += f"{reach_display} "
            if thrown_range_display:
                strike_line += f"{thrown_range_display}, " # Add comma if there's a range
            strike_line += "one target."

            if damage_display:
                strike_line += f" Hit: {damage_display}."
            if cleaned_desc:
                strike_line += f" {cleaned_desc}"
            content_html += f"<p style=\"box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;\">{strike_line}</p>"
        elif item.get('type') == 'spell':
            spell_level = item['system']['level'].get('value', '')
            spell_time = item['system']['time'].get('value', '')
            spell_range = item['system']['range'].get('value', '')
            spell_target = item['system']['target'].get('value', '')
            
            spell_line = f"<strong style=\"box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;\">{name_display} (Level {spell_level}).</strong> {action_symbol} Cast: {spell_time}. Range: {spell_range}. Target: {spell_target}."
            if cleaned_desc:
                spell_line += f" {cleaned_desc}"
            content_html += f"<p style=\"box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;\">{spell_line}</p>"
        elif item.get('type') in ['weapon', 'armor', 'consumable']:
            # Handle equipment: name and description
            item_desc = _clean_description_html(item.get('system', {}).get('description', {}).get('value', ''))
            content_html += f"""<p style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;"><strong style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{name_display}.</strong>&nbsp;{item_desc}</p>"""
        else: # For actions and general traits/abilities
            content_html += f"""<p style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;"><strong style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{name_display}.</strong>&nbsp;{cleaned_desc}</p>"""
            
    return f"""
<div class="mon-stat-block__description-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
    <div class="mon-stat-block__description-block-heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: rgb(0, 0, 0); color: rgb(0, 0, 0); font-size: 24px; line-height: 1.4; margin-top: 20px; margin-bottom: 15px;">{heading_text}</div>
    <div class="mon-stat-block__description-block-content" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        {content_html}
    </div>
</div>
"""

def format_monster_notes(monster_data):
    """
    Formats various attributes of a monster into a comprehensive HTML string
    mimicking D&D Beyond stat block styling for the 'notes' field.
    All href links and PF2e UUIDs are removed.
    """
    
    # Public Notes / Blurb - will be moved to the end
    public_notes_content = monster_data['system']['details'].get('publicNotes', '')
    
    header_html = _generate_header_html(monster_data)
    attributes_html = _generate_attributes_html(monster_data)
    ability_scores_html = _generate_ability_scores_html_for_main_block(monster_data)
    tidbits_html = _generate_tidbits_html(monster_data)

    # Separate items into categories for display
    spellcasting_entries = {} # Key: spellcastingEntry._id, Value: {data, spells:[]}
    actions = []
    strikes = []
    traits = [] # For passive abilities/traits not tied to PF2e 'action' type
    equipment = [] # Weapons, Armor, Consumables

    for item in monster_data.get('items', []):
        if item.get('type') == 'spellcastingEntry':
            spellcasting_entries[item['_id']] = {'data': item, 'spells': []}
        elif item.get('type') == 'spell':
            # Spells are associated with a spellcasting entry by system.location.value
            location_id = item['system']['location'].get('value')
            if location_id and location_id in spellcasting_entries:
                spellcasting_entries[location_id]['spells'].append(item)
            else:
                # If a spell has no associated entry, treat as a trait
                traits.append(item)
        elif item.get('type') == 'melee': # PF2e uses 'melee' type for NPC strikes (both melee and ranged)
            strikes.append(item)
        elif item.get('type') == 'action':
            if item['system']['actionType'].get('value') == 'passive':
                traits.append(item) # Treat passive actions as traits
            else:
                actions.append(item) # Regular actions and reactions
        elif item.get('type') in ['weapon', 'armor', 'consumable']:
            equipment.append(item)


    traits_html = _generate_description_block_html("Traits", traits)
    strikes_html = _generate_description_block_html("Strikes", strikes)
    actions_html = _generate_description_block_html("Actions", actions)
    equipment_html = _generate_description_block_html("Equipment", equipment) # New section for equipment

    spellcasting_html = ""
    for entry_id, entry_data in spellcasting_entries.items():
        spell_list_html = ""
        # Sort spells by level and then name for consistent output
        sorted_spells = sorted(entry_data['spells'], key=lambda s: (s['system']['level'].get('value', 0), s.get('name', '')))
        for spell in sorted_spells:
            spell_desc = _clean_description_html(spell['system']['description'].get('value', ''))
            # Include time, range, target for spells if available
            spell_time = spell['system']['time'].get('value', '')
            spell_range = spell['system']['range'].get('value', '')
            spell_target = spell['system']['target'].get('value', '')
            
            spell_details = []
            if spell_time: spell_details.append(f"Cast: {spell_time}")
            if spell_range: spell_details.append(f"Range: {spell_range}")
            if spell_target: spell_details.append(f"Target: {spell_target}")
            
            details_str = ", ".join(spell_details)
            if details_str:
                details_str = f" ({details_str})"

            spell_list_html += f"<p style=\"box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 5px;\"><strong style=\"box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;\">{spell.get('name', 'Unknown Spell')} (Level {spell['system']['level']['value']}).</strong>{details_str} {spell_desc}</p>"
        
        if spell_list_html:
            spellcasting_html += f"""
<div class="mon-stat-block__description-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
    <div class="mon-stat-block__description-block-heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-bottom-width: 1px; border-bottom-color: rgb(0, 0, 0); color: rgb(0, 0, 0); font-size: 24px; line-height: 1.4; margin-top: 20px; margin-bottom: 15px;">{entry_data['data'].get('name', 'Spellcasting')}</div>
    <div class="mon-stat-block__description-block-content" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        {spell_list_html}
    </div>
</div>
"""


    # Combine all parts into the final HTML string, following the nested structure
    full_notes_html = f"""
<div class="mon-stat-block__header" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; line-height: 1.1; background-color: rgb(255, 255, 255);">
    <div class="mon-stat-block__name" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        <div class="name" style="">
            <h1 style="padding: 0px; letter-spacing: 1px; color: rgb(0, 0, 0); font-size: 1.6rem; line-height: 1; break-after: avoid;">
                {header_html}
                <hr style="border: none; border-top: 1px solid rgb(0, 0, 0); margin: 10px 0;">
                {attributes_html}
                <hr style="border: none; border-top: 1px solid rgb(0, 0, 0); margin: 10px 0;">
                <div class="mon-stat-block__stat-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-size: 14px;">
                    <hr style="border: none; border-top: 1px solid rgb(0, 0, 0); margin: 10px 0;">
                    <div class="ability-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex; flex-wrap: wrap; margin: 0px; color: rgb(0, 0, 0);">
                        {ability_scores_html}
                    </div>
                    <hr style="border: none; border-top: 1px solid rgb(0, 0, 0); margin: 10px 0;">
                </div>
                <div class="mon-stat-block__tidbits" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-size: 14px;">
                    {tidbits_html}
                </div>
                <hr style="border: none; border-top: 1px solid rgb(0, 0, 0); margin: 10px 0;">
                <div class="mon-stat-block__description-blocks" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-top: 20px; color: rgb(0, 0, 0); font-size: 14px;">
                    {traits_html}
                    {strikes_html}
                    {actions_html}
                    {spellcasting_html}
                    {equipment_html}
                </div>
                {'' if not public_notes_content else f'''
                <hr style="border: none; border-top: 1px solid rgb(0, 0, 0); margin: 10px 0;">
                <div class="public-notes" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 15px; font-size: 12px; line-height: 1.5;">{_clean_description_html(public_notes_content)}</div>
                '''}
            </h1>
        </div>
    </div>
</div>
"""
    return full_notes_html

def _process_single_monster_file(filepath):
    """
    Loads a single JSON file, checks if it's an 'npc' type, and converts it.
    Returns the converted monster data or None if not an 'npc' or on error.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            monster_data = json.load(f)
        
        # Omit entry if the name is missing
        monster_name = monster_data.get('name')
        if not monster_name:
            print(f"Skipping {filepath}: monster name is missing.")
            return None

        # Check if it's an 'npc' type as specified
        if monster_data.get('type') != 'npc':
            # print(f"Skipping {filepath}: 'type' is not 'npc'.")
            return None

        # Extract PF2e specific HP
        hp_value = monster_data['system']['attributes']['hp'].get('value', 0)
        hp_max = monster_data['system']['attributes']['hp'].get('max', hp_value) # Use value as fallback if max is not defined

        # Get level for 'challenge' field
        level = monster_data['system']['details'].get('level', {}).get('value', 'N/A')
        
        # Get perception mod for initiative bonus
        initiative_bonus = monster_data['system']['perception'].get('mod', 0)

        converted_monster = {
            "name": monster_name,
            "hp": str(hp_value),
            "totalHp": str(hp_max),
            "initiativeBonus": initiative_bonus,
            "version": "pf2e", 
            "challenge": f"Level {level}",
            "notes": format_monster_notes(monster_data)
        }
        return converted_monster

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Please ensure it's valid JSON.")
        return None
    except Exception as e:
        print(f"Warning: Failed to process file '{filepath}' due to: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return None

def convert_monster_data(input_directory_path, output_json_path, limit=None):
    """
    Walks through a directory, processes individual JSON files, and converts them.
    Includes a limit to stop processing after a certain number of monsters.
    """
    if not os.path.isdir(input_directory_path):
        print(f"Error: Input path '{input_directory_path}' is not a valid directory.")
        return

    all_converted_monsters = []
    
    print(f"Scanning directory: {input_directory_path} for monster files...")
    
    for root, _, files in os.walk(input_directory_path):
        # Check limit before processing each dir
        if limit is not None and len(all_converted_monsters) >= limit:
            print(f"Limit of {limit} successfully converted monsters reached. Stopping scan.")
            break # Break out of the os.walk loop
        for filename in files:
            # Check limit before processing each file
            if limit is not None and len(all_converted_monsters) >= limit:
                print(f"Limit of {limit} successfully converted monsters reached. Stopping scan.")
                break # Break out of the current files loop
            
            if filename.endswith('.json'):
                filepath = os.path.join(root, filename)                
                converted_monster = _process_single_monster_file(filepath)
                if converted_monster:
                    print(f"Converted file: {filepath}")
                    all_converted_monsters.append(converted_monster)

    if not all_converted_monsters:
        print("No 'npc' type monster files found or processed in the specified directory.")
        return

    # Sort the monsters alphabetically by name before writing to file
    all_converted_monsters.sort(key=lambda m: m.get('name', '').lower())

    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_converted_monsters, f, indent=2, ensure_ascii=False)
        print(f"Successfully converted {len(all_converted_monsters)} monsters to {output_json_path}")
    except IOError as e:
        print(f"Error writing to output file {output_json_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert D&D monster data from a directory of JSON files to Initiative Tracker format.")
    parser.add_argument("input_directory", type=str, help="Path to the input directory containing monster JSON files.")
    parser.add_argument("output_file", type=str, default="converted_monsters.json", help="Path for the output JSON file in Initiative Tracker format.")
    parser.add_argument("--limit", type=int, help="Limit the number of monsters to parse.")
    
    args = parser.parse_args()
    
    convert_monster_data(args.input_directory, args.output_file, args.limit)
