Description
===========
Ce programme récupère les statistiques de la freebox à l'URL
http://mafreebox.freebox.fr/pub/fbx_info.txt et les stocke dans une base de
données sqlite.

Utilisation
===========
    usage: ./fbx-update-stats.py [-h] [-d DATABASE] [-u URL]

L'option `-d` ou `--database` spécifie le chemin vers le fichier où sera
stockée la base de données sqlite.

L'option `-u` ou `--url` spécifie une URL alternative. Elle peut notamment être
utilisée pour spécifier une URL qui n'utilise pas le nom de domaine
`mafreebox.freebox.fr` mais l'adresse IP directement.
