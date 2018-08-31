import obspython as obs
import urllib.request
import urllib.error
import json
import re
import os

source_name = ""
source_top5 = ""
ip_address  = ""
user_name   = ""
lastEvt = 0
lastDmg = 0
maxLen = 0
topsize = 5
stats = {}
shows = {}
obsData = ""
trying = False
doParse = False
debug = False

# ------------------------------------------------------------

def cleanname(name):
	global maxLen
#	(ger)(isr)(ussr)(usa)(uk)(jp)
	res = name.strip('▀\uf059▂▃▄▅')
	if len(res) > maxLen:
		maxLen = len(res)
	return res

def addkill(key):
	global stats
	key = cleanname(key)
	stats['kills'] += 1
	if key in stats['k']:
		stats['k'][key] += 1
	else:
		stats['k'][key] = 1
	if key not in stats['d']:
		stats['d'][key] = 0

def adddeath(key):
	global stats
	key = cleanname(key)
	stats['deaths'] += 1
	if key in stats['d']:
		stats['d'][key] +=1
	else:
		stats['d'][key] = 1
	if key not in stats['k']:
		stats['k'][key] = 0

def addburn():
	global stats
	stats['burns'] += 1

def addmedal():
	global stats
	stats['medals'] += 1

def addcrit():
	global stats
	stats['crits'] += 1

def parse_damage(msg):
	global user_name
	global stats
	m = re.match("([^(]+) \((.+)\) сбил ([^(]+) \((.+)\)", msg)
	if m:
		if m.group(1) == user_name:
			addkill(m.group(2))
		if m.group(3) == user_name:
			adddeath(m.group(4))
		log("Rule 1")
		return
	m = re.match("([^(]+) \((.+)\) уничтожил ([^(]+) \((.+)\)", msg)
	if m:
		if m.group(1) == user_name:
			addkill(m.group(2))
		if m.group(3) == user_name:
			adddeath(m.group(4))
		log("Rule 2")
		return
	m = re.match("([^(]+) \((.+)\) разбился", msg)
	if m:
		if m.group(1) == user_name:
			adddeath(m.group(2))
		log("Rule 3")
		return
	m = re.match("([^(]+) \((.+)\) выведен из строя", msg)
	if m:
		if m.group(1) == user_name:
			adddeath(m.group(2))
		log("Rule 4")
		return
	m = re.match("([^(]+) \((.+)\) получил \"(.+)\"", msg)
	if m:
		if m.group(1) == user_name:
			addmedal()
		log("Rule 5")
		return
	m = re.match("([^(]+) \((.+)\) подбил ([^(]+) \((.+)\)", msg)
	if m:
		if m.group(1) == user_name:
			addcrit()
		log("Rule 6")
		return
	m = re.match("([^(]+) \((.+)\) поджёг ([^(]+) \((.+)\)", msg)
	if m:
		if m.group(1) == user_name:
			addburn()
		log("Rule 7")
		return
	m = re.match("([^(]+) \((.+)\) нанёс последний удар!", msg)
	if m:
		log("Rule 8")
		return
	m = re.match("([^(]+) \((.+)\) ударил первым!", msg)
	if m:
		log("Rule 9")
		return
	m = re.match("(.+) присоединился к событию", msg)
	if m:
		log("Rule 10")
		return
	m = re.match("(.+) сбил ([^(]+) \((.+)\)", msg)
	if m:
		if m.group(2) == user_name:
			adddeath(m.group(3))
		log("Rule 11")
		return
	m = re.match("(.+) уничтожил ([^(]+) \((.+)\)", msg)
	if m:
		if m.group(2) == user_name:
			adddeath(m.group(3))
		log("Rule 12")
		return
	m = re.match("(.+) сбил (.+)", msg)
	if m:
		log("Rule 13")
		return
	m = re.match("(.+) уничтожил (.+)", msg)
	if m:
		log("Rule 14")
		return
	m = re.match("(.+) подбил (.+)", msg)
	if m:
		log("Rule 15")
		return
	m = re.match("(.+) поджёг (.+)", msg)
	if m:
		log("Rule 16")
		return
	log("Not parsed: " + msg)

def make_text():
	global stats
	global shows
	res = ""
	if shows['kills']:
		res += "Убийств:  " + str(stats['kills']) + "\n"
	if shows['deaths']:
		res += "Смертей:  " + str(stats['deaths']) + "\n"
	if shows['burns']:
		res += "Поджогов: " + str(stats['burns']) + "\n"
	if shows['crits']:
		res += "Критов:   " + str(stats['crits']) + "\n"
	if shows['medals']:
		res += "Наград:   " + str(stats['medals']) + "\n"
	return res.strip()

def make_top():
	global stats
	global maxLen
	global topsize
	res = ""
	i = 0
	for key in sorted(stats['k'], key=stats['k'].__getitem__, reverse=True):
		if i == topsize:
			break
		else:
			i += 1
		res += key.ljust(maxLen) + " " + str(stats['k'][key]) + "/" + str(stats['d'][key]) + "\n"
	return res.strip()

def log(msg):
	global debug
	if debug:
		with open(os.path.realpath(__file__)+"_battle.log","a", encoding="utf-8") as f:
			f.write(str(msg)+"\n")
		f.close()
	
def update_text():
	global source_name
	global source_top5
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
					log(dmg)
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
	source = obs.obs_get_source_by_name(source_top5)
	if source is not None:
		settings = obs.obs_data_create()
		obs.obs_data_set_string(settings, "text", make_top())
		obs.obs_source_update(source, settings)
		obs.obs_data_release(settings)
		obs.obs_source_release(source)
	trying = False

def reset_stat():
	global stats
	stats={}
	stats['k']={}
	stats['d']={}
	stats['kills'] = 0
	stats['burns'] = 0
	stats['deaths'] = 0	
	stats['medals'] = 0
	stats['crits'] = 0

def save_stat():
	global stats
	with open(os.path.realpath(__file__)+"_save.dat","w", encoding="utf-8") as f:
		json.dump(stats, f)
	f.close()

def load_stat():
	global stats
	global maxLen
	with open(os.path.realpath(__file__)+"_save.dat","r", encoding="utf-8") as f:
		stats = json.load(f)
	f.close()
	maxLen = 0
	for k in stats['k'].keys():
		if len(k) > maxLen:
			maxLen = len(k)

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
	reset_stat()

def save_pressed(props, prop):
	save_stat()

def load_pressed(props, prop):
	load_stat()

# --- OBS exports
	
def script_load(settings):
	global obsData
	obsData = settings
	reset_stat()
	load_stat()

def script_unload():
	save_stat()

def script_defaults(settings):
	obs.obs_data_set_default_string(settings, "ip_address", "127.0.0.1:8111")
	obs.obs_data_set_default_int(settings, "topsize", 5)
	obs.obs_data_set_default_bool(settings, "skills", True)
	obs.obs_data_set_default_bool(settings, "sdeaths", True)
	obs.obs_data_set_default_bool(settings, "sburns", False)
	obs.obs_data_set_default_bool(settings, "scrits", False)
	obs.obs_data_set_default_bool(settings, "smedals", False)
	
def script_description():
	return "WT Писькомер v. 0.005\n(cc) ZorroGFS"

def script_update(settings):
	global source_name
	global source_top5
	global ip_address
	global user_name
	global shows
	global topsize
	source_name    = obs.obs_data_get_string(settings, "source")
	source_top5    = obs.obs_data_get_string(settings, "sourcetop")
	ip_address  = obs.obs_data_get_string(settings, "ip_address")
	user_name   = obs.obs_data_get_string(settings, "user_name")
	shows['kills'] = obs.obs_data_get_bool(settings, "skills")
	shows['deaths'] = obs.obs_data_get_bool(settings, "sdeaths")
	shows['burns'] = obs.obs_data_get_bool(settings, "sburns")
	shows['crits'] = obs.obs_data_get_bool(settings, "scrits")
	shows['medals'] = obs.obs_data_get_bool(settings, "smedals")
	topsize = obs.obs_data_get_int(settings, "topsize")
	obs.timer_remove(update_text)
	if ip_address != "" and source_name != "" and user_name != "":
		obs.timer_add(update_text, 1000)

def script_properties():
	props = obs.obs_properties_create()
	obs.obs_properties_add_text(props, "ip_address", "Адрес WT", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(props, "user_name", "Ник в игре", obs.OBS_TEXT_DEFAULT)
	p = obs.obs_properties_add_list(props, "source", "Поле статистики", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
	sources = obs.obs_enum_sources()
	if sources is not None:
		for source in sources:
			source_id = obs.obs_source_get_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source":
				name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(p, name, name)
		obs.source_list_release(sources)
	p = obs.obs_properties_add_list(props, "sourcetop", "Поле топа техники", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
	sources = obs.obs_enum_sources()
	if sources is not None:
		for source in sources:
			source_id = obs.obs_source_get_id(source)
			if source_id == "text_gdiplus" or source_id == "text_ft2_source":
				name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(p, name, name)
		obs.source_list_release(sources)
	obs.obs_properties_add_int(props, "topsize", "Размер топа", 3, 20, 1)
	obs.obs_properties_add_bool(props, "skills", "Отображать убийства")
	obs.obs_properties_add_bool(props, "sdeaths", "Смерти")
	obs.obs_properties_add_bool(props, "sburns", "Поджоги")
	obs.obs_properties_add_bool(props, "scrits", "Криты")
	obs.obs_properties_add_bool(props, "smedals", "Награды")
	obs.obs_properties_add_button(props, "button1", "Сброс статистики", statreset_pressed)
	obs.obs_properties_add_button(props, "button_save", "Сохранить статистику", save_pressed)
	obs.obs_properties_add_button(props, "button_load", "Загрузить статистику", load_pressed)
	obs.obs_properties_add_button(props, "button2", "Переподключиться к WT", refresh_pressed)
	return props
