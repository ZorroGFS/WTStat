import obspython as obs
import urllib.request
import urllib.error
import json
import re
import os

source_name = ""
ip_address  = ""
user_name   = ""
lastEvt = 0
lastDmg = 0
stats = {}
obsData = ""
trying = False
doParse = False

# ------------------------------------------------------------

def parse_damage(msg):
	global user_name
	global stats
	m = re.match("(.*) \((.*)\) сбил (.*) \((.*)\)", msg)
	if m:
		if m.group(1) == user_name:
			stats['kills']+=1
		if m.group(3) == user_name:
			stats['deaths']+=1
		return
	m = re.match("(.*) \((.*)\) уничтожил (.*) \((.*)\)", msg)
	if m:
		if m.group(1) == user_name:
			stats['kills']+=1
		if m.group(3) == user_name:
			stats['deaths']+=1
		return
	m = re.match("(.*) \((.*)\) разбился", msg)
	if m:
		if m.group(1) == user_name:
			stats['deaths']+=1
		return
	m = re.match("(.*) \((.*)\) выведен из строя", msg)
	if m:
		if m.group(1) == user_name:
			stats['deaths']+=1
		return
	m = re.match("(.*) \((.*)\) получил \"(.*)\"", msg)
	if m:
		return
	m = re.match("(.*) \((.*)\) подбил (.*) \((.*)\)", msg)
	if m:
		return
	m = re.match("(.*) \((.*)\) поджёг (.*) \((.*)\)", msg)
	if m:
		if m.group(1) == user_name:
			stats['burns']+=1
		return
	m = re.match("(.*) \((.*)\) нанёс последний удар!", msg)
	if m:
		return
	m = re.match("(.*) \((.*)\) ударил первым!", msg)
	if m:
		return
	m = re.match("(.*) присоединился к событию", msg)
	if m:
		return
	m = re.match("(.*) сбил (.*) \((.*)\)", msg)
	if m:
		if m.group(2) == user_name:
			stats['deaths']+=1
		return
	m = re.match("(.*) уничтожил (.*) \((.*)\)", msg)
	if m:
		if m.group(2) == user_name:
			stats['deaths']+=1
		return
	m = re.match("(.*) сбил (.*)", msg)
	if m:
		return
	m = re.match("(.*) уничтожил (.*)", msg)
	if m:
		return
	log("Not parsed: " + msg)

def make_text():
	global stats
	res =  "Убийств: " + str(stats['kills']) + "\n"
	res += "Поджогов: " + str(stats['burns']) + "\n"
	res += "Смертей: " + str(stats['deaths'])
	return res

def log(msg):
	f = open(os.path.realpath(__file__)+"_battle.log","a", encoding="utf-8")
	try:
		f.write(str(msg)+"\n")
	finally:
		f.close()
	
def update_text():
	global source_name
	global ip_address
	global lastEvt
	global lastDmg
	global trying
	global doParse
	if trying:
		return
	trying = True
	url = "http://" + ip_address + "/hudmsg?lastEvt=" + str(lastEvt) + "&lastDmg=" + str(lastDmg)
	source = obs.obs_get_source_by_name(source_name)
	if source is not None:
		try:
			with urllib.request.urlopen(url) as response:
				data = response.read()
				text = data.decode('utf-8')
				js = json.loads(text)
				for evt in js['events']:
					lastEvt = evt['id']
				for dmg in js['damage']:
#					log(dmg)
					lastDmg = dmg['id']
					if doParse:
						parse_damage(dmg['msg'])
				if not doParse:
					obs.script_log(obs.LOG_WARNING, "Connected")
					doParse = True
				settings = obs.obs_data_create()
				obs.obs_data_set_string(settings, "text", make_text())
				obs.obs_source_update(source, settings)
				obs.obs_data_release(settings)
		except urllib.error.URLError as err:
			obs.script_log(obs.LOG_WARNING, "Error opening URL '" + url + "': " + str(err.reason))
			obs.remove_current_callback()
		obs.obs_source_release(source)
	trying = False

# --- Buttons
	
def refresh_pressed(props, prop):
	global lastEvt
	global lastDmg
	global doParse
	global obsData
	doParse = False
	lastDmg = 0
	lastEvt = 0
	script_update(obsData)

def statreset_pressed(props, prop):
	global stats
	global obsData
	stats['kills'] = obs.obs_data_get_int(obsData, "ikills")
	stats['burns'] = obs.obs_data_get_int(obsData, "iburns")
	stats['deaths'] = obs.obs_data_get_int(obsData, "ideaths")

# --- OBS exports
	
def script_load(settings):
	global stats
	global obsData
	obsData = settings
	stats['kills'] = 0
	stats['burns'] = 0
	stats['deaths'] = 0

def script_defaults(settings):
	obs.obs_data_set_default_string(settings, "ip_address", "127.0.0.1:8111")
	
def script_description():
	return "WT Писькомер v. 0.001\n(cc) ZorroGFS"

def script_update(settings):
	global source_name
	global ip_address
	global user_name
	global stats
	source_name    = obs.obs_data_get_string(settings, "source")
	ip_address  = obs.obs_data_get_string(settings, "ip_address")
	user_name   = obs.obs_data_get_string(settings, "user_name")
	stats['kills'] = obs.obs_data_get_int(obsData, "ikills")
	stats['burns'] = obs.obs_data_get_int(obsData, "iburns")
	stats['deaths'] = obs.obs_data_get_int(obsData, "ideaths")
	obs.timer_remove(update_text)
	if ip_address != "" and source_name != "" and user_name != "":
		obs.timer_add(update_text, 1000)

def script_properties():
	props = obs.obs_properties_create()
	obs.obs_properties_add_text(props, "ip_address", "Адрес WT", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(props, "user_name", "Ник в игре", obs.OBS_TEXT_DEFAULT)
	p = obs.obs_properties_add_list(props, "source", "Поле в OBS", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
	sources = obs.obs_enum_sources()
	if sources is not None:
		for source in sources:
			source_id = obs.obs_source_get_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source":
				name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(p, name, name)
		obs.source_list_release(sources)
	obs.obs_properties_add_int(props, "ikills", "Убийств", 0, 1000, 1)
	obs.obs_properties_add_int(props, "iburns", "Поджогов", 0, 1000, 1)
	obs.obs_properties_add_int(props, "ideaths", "Смертей", 0, 1000, 1)
	obs.obs_properties_add_button(props, "button1", "Сброс значений", statreset_pressed)
	obs.obs_properties_add_button(props, "button2", "Переподключиться к WT", refresh_pressed)
	return props
