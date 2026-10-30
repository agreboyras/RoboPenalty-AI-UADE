"""PowerShell input/state rules, without installing packages or external resources."""
import base64
import json
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class StudentInstallTests(unittest.TestCase):
    def ps(self,expression,answer=''):
        helper=str(ROOT/'scripts/_install_input.ps1').replace("'","''")
        answer=answer.replace("'","''")
        boot=("$ErrorActionPreference='Stop'; . '"+helper+"'; $global:reads=0; "
              "function Read-Host { param($Prompt); $global:reads++; return '"+answer+"' }; ")
        code=boot+expression
        encoded=base64.b64encode(code.encode('utf-16-le')).decode()
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','RemoteSigned','-EncodedCommand',encoded],
                              cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,encoding='utf-8',errors='replace')

    def value(self,expr,answer=''):
        p=self.ps(expr+' | ConvertTo-Json -Compress',answer)
        self.assertEqual(p.returncode,0,p.stderr)
        return json.loads(p.stdout.strip().splitlines()[-1])

    def test_mutually_exclusive_flags(self):
        self.assertNotEqual(self.ps('Resolve-InstallInteraction -Interactivo -NoInteractivo').returncode,0)

    def test_no_interaction_is_explicit(self):
        self.assertFalse(self.value('Resolve-InstallInteraction -NoInteractivo'))

    def test_force_interaction(self):
        self.assertTrue(self.value('Resolve-InstallInteraction -Interactivo'))

    def test_redirected_default_does_not_prompt(self):
        self.assertFalse(self.value('Resolve-InstallInteraction'))

    def folder(self,args,answer=''):
        return self.value('$folder=Get-InstallDeployFolder '+args+'; [pscustomobject]@{folder=$folder;reads=$global:reads}',answer)

    def test_explicit_path_with_spaces_never_prompts(self):
        self.assertEqual(self.folder("-ExplicitPath '../Deploy Provided' -Needed $true -Ask $true"),dict(folder='../Deploy Provided',reads=0))

    def test_complete_resources_do_not_prompt(self):
        self.assertEqual(self.folder('-Needed $false -Ask $true'),dict(folder='',reads=0))

    def test_noninteractive_missing_stays_empty(self):
        self.assertEqual(self.folder('-Needed $true -Ask $false'),dict(folder='',reads=0))

    def test_prompt_trims_quotes_and_empty_choice(self):
        for answer,expected in [('  "../Deploy Provided"  ','../Deploy Provided'),('','')]:
            with self.subTest(answer=answer):
                self.assertEqual(self.folder('-Needed $true -Ask $true',answer),dict(folder=expected,reads=1))

    def details(self,change=''):
        boot=("$targets=@(0..25 | ForEach-Object { [pscustomobject]@{target=('RoboNaldo_Deploy/file'+$_)} }); "
              "$problems=@($targets | ForEach-Object { [pscustomobject]@{kind='missing';resource=$_.target} }); "+change+
              "$details=[pscustomobject]@{licensing=[pscustomobject]@{resources=$targets};external=[pscustomobject]@{problems=$problems}}; ")
        return self.value(boot+'Test-OnlyExpectedDeployMissing -Details $details')

    def test_exact_expected_missing_is_partial(self):
        self.assertTrue(self.details())

    def test_integrity_errors_duplicates_other_missing_are_not_partial(self):
        for change in ("$problems[0].kind='different'; ","$problems[0].resource='other/resource'; ","$problems[0].resource=$problems[1].resource; "):
            with self.subTest(change=change):self.assertFalse(self.details(change))


if __name__=='__main__':unittest.main(verbosity=2)
