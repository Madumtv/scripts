import sys
import os
import json
import shlex
import webbrowser
import paramiko
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox,
                               QComboBox, QTabWidget, QTextEdit, QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox, QCheckBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QDateTime

BASE_DOCROOT = "/var/www"
CONFIG_FILE = "config.json"

class ApacheManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apache VPS Manager")
        self.resize(700, 500)
        self.ssh_client = None

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # -- Onglet Gestionnaire --
        self.manager_tab = QWidget()
        self.layout = QVBoxLayout()
        self.manager_tab.setLayout(self.layout)
        self.tabs.addTab(self.manager_tab, "Gestionnaire")

        # -- Onglet Logs --
        self.log_tab = QWidget()
        self.log_layout = QVBoxLayout()
        self.log_tab.setLayout(self.log_layout)
        self.tabs.addTab(self.log_tab, "Logs")

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        font = QFont("Consolas", 9)
        self.log_output.setFont(font)
        self.log_layout.addWidget(self.log_output)

        # --- Connexion ---
        self.layout.addWidget(QLabel("Connexion au VPS", alignment=Qt.AlignCenter))
        self.layout.addSpacing(10)
        
        self.profiles = {}

        profile_layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.load_profile_data)
        
        self.profile_name_input = QLineEdit()
        self.profile_name_input.setPlaceholderText("Nom du profil (ex: Prod)")
        self.profile_name_input.setFixedWidth(200)
        
        profile_layout.addWidget(QLabel("Profil:"))
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addWidget(self.profile_name_input)
        self.layout.addLayout(profile_layout)

        form_layout = QHBoxLayout()
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("IP du VPS")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Utilisateur SSH")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setPlaceholderText("Mot de passe")

        form_layout.addWidget(self.host_input)
        form_layout.addWidget(self.user_input)
        form_layout.addWidget(self.pass_input)

        self.layout.addLayout(form_layout)

        # Champ domaine de base (optionnel)
        domain_layout = QHBoxLayout()
        self.base_domain_input = QLineEdit()
        self.base_domain_input.setPlaceholderText("Domaine de base (ex: madum.top) - Optionnel")
        domain_layout.addWidget(QLabel("Domaine associé :"))
        domain_layout.addWidget(self.base_domain_input)
        self.layout.addLayout(domain_layout)

        self.connect_btn = QPushButton("Se connecter")
        self.connect_btn.clicked.connect(self.connect_ssh)
        self.layout.addWidget(self.connect_btn, alignment=Qt.AlignCenter)

        # --- Menu après connexion ---
        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout()
        self.menu_widget.setLayout(self.menu_layout)
        self.menu_widget.setVisible(False)

        self.site_list = QListWidget()
        self.menu_layout.addWidget(QLabel("Sites disponibles :"))
        self.menu_layout.addWidget(self.site_list)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter un site")
        self.add_btn.clicked.connect(self.add_site)
        self.remove_btn = QPushButton("Supprimer le site")
        self.remove_btn.clicked.connect(self.remove_site)
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self.list_sites)
        self.reload_btn = QPushButton("Recharger Apache")
        self.reload_btn.clicked.connect(self.reload_apache)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.reload_btn)

        self.menu_layout.addLayout(btn_layout)
        
        nav_layout = QHBoxLayout()
        self.open_pma_btn = QPushButton("Ouvrir phpMyAdmin")
        self.open_pma_btn.clicked.connect(self.open_phpmyadmin)
        
        nav_layout.addWidget(self.open_pma_btn)
        
        self.menu_layout.addLayout(nav_layout)
        self.layout.addWidget(self.menu_widget)
        
        # --- Pied de page ---
        footer_layout = QHBoxLayout()
        self.quit_btn = QPushButton("Quitter")
        self.quit_btn.clicked.connect(self.close)
        self.quit_btn.setFixedWidth(100)
        footer_layout.addStretch()
        footer_layout.addWidget(self.quit_btn)
        self.main_layout.addLayout(footer_layout)
        
        self.load_config()

    def load_config(self):
        self.profiles = {}
        last_profile = ""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.profiles = config.get("profiles", {})
                    last_profile = config.get("last_profile", "")
            except Exception as e:
                self.log(f"Erreur config: {e}")

        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Nouveau profil...")
        for name in self.profiles:
            self.profile_combo.addItem(name)
        self.profile_combo.blockSignals(False)

        if last_profile in self.profiles:
            self.profile_combo.setCurrentText(last_profile)
            self.load_profile_data()

    def load_profile_data(self):
        name = self.profile_combo.currentText()
        if name == "Nouveau profil...":
            for i in [self.profile_name_input, self.host_input, self.user_input, self.pass_input, self.base_domain_input]: i.clear()
        elif name in self.profiles:
            prof = self.profiles[name]
            self.profile_name_input.setText(name)
            self.host_input.setText(prof.get("host", ""))
            self.user_input.setText(prof.get("user", ""))
            self.pass_input.setText(prof.get("password", ""))
            self.base_domain_input.setText(prof.get("base_domain", ""))

    def save_config(self, host, user, password, base_domain=""):
        profile_name = self.profile_name_input.text().strip() or host
        if profile_name in self.profiles:
            # Conserver les données existantes (comme 'sites')
            self.profiles[profile_name].update({
                "host": host,
                "user": user,
                "password": password,
                "base_domain": base_domain
            })
        else:
            self.profiles[profile_name] = {
                "host": host,
                "user": user,
                "password": password,
                "base_domain": base_domain,
                "sites": {}
            }
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"profiles": self.profiles, "last_profile": profile_name}, f, indent=4)
        except Exception as e: self.log(f"Erreur sauvegarde: {e}")

    def save_site_info(self, domain, db_data):
        profile_name = self.profile_name_input.text().strip() or self.host_input.text().strip()
        if profile_name not in self.profiles: return
        
        if "sites" not in self.profiles[profile_name]:
            self.profiles[profile_name]["sites"] = {}
            
        self.profiles[profile_name]["sites"][domain] = db_data
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"profiles": self.profiles, "last_profile": profile_name}, f, indent=4)
        except Exception as e: self.log(f"Erreur sauvegarde site: {e}")

    def connect_ssh(self):
        host, user, password = self.host_input.text().strip(), self.user_input.text().strip(), self.pass_input.text().strip()
        base_domain = self.base_domain_input.text().strip()
        if not all([host, user, password]): return
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(hostname=host, username=user, password=password)
            self.ssh_client = client
            self.save_config(host, user, password, base_domain)
            self.menu_widget.setVisible(True)
            self.connect_btn.setEnabled(False)
            self.list_sites()
        except Exception as e: QMessageBox.critical(self, "Erreur SSH", str(e))

    def log(self, message):
        line = f"[{QDateTime.currentDateTime().toString('HH:mm:ss')}] {message}"
        self.log_output.append(line)

    def run_cmd(self, cmd):
        self.log(f"> {cmd}")
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        return stdout.read().decode().strip(), stderr.read().decode().strip()

    def run_sudo_cmd(self, cmd):
        if self.user_input.text().strip() == "root": return self.run_cmd(cmd)
        pwd = shlex.quote(self.pass_input.text())
        return self.run_cmd(f"echo {pwd} | sudo -S bash -c {shlex.quote(cmd)}")

    def list_sites(self):
        out, _ = self.run_cmd("ls /etc/apache2/sites-available")
        self.site_list.clear()
        
        # Identifier les sites avec SSL
        available_files = out.splitlines()
        sites_ssl = {}
        for line in available_files:
            if not line.strip() or line in ["default-ssl.conf", "000-default.conf"]: continue
            if "-le-ssl.conf" in line:
                domain = line.replace("-le-ssl.conf", "")
                sites_ssl[domain] = True
            elif line.endswith(".conf"):
                domain = line.replace(".conf", "")
                if domain not in sites_ssl:
                    sites_ssl[domain] = False

        sites = sorted(sites_ssl.keys())
        for s in sites:
            if not s.strip(): continue
            has_ssl = sites_ssl[s]
            item = QListWidgetItem()
            item.setData(Qt.UserRole, s)
            self.site_list.addItem(item)
            
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(5, 2, 5, 2)
            
            icon_lbl = QLabel("🔒" if has_ssl else ("🔓" if "." in s else "📁"))
            if has_ssl:
                icon_lbl.setStyleSheet("color: #4CAF50; font-size: 14px;")
            elif "." in s:
                icon_lbl.setStyleSheet("color: #F44336; font-size: 14px;")
            else:
                icon_lbl.setStyleSheet("color: #2196F3; font-size: 14px;")
                
            lbl = QLabel(s)
            
            # Boutons Actions
            btn_open = QPushButton("Ouvrir")
            btn_open.clicked.connect(lambda *args, domain=s, secure=has_ssl: self.open_site(domain, secure))

            btn_pma = QPushButton("PMA")
            btn_pma.setFixedWidth(40)
            btn_pma.setToolTip("Accès phpMyAdmin")
            
            profile_name = self.profile_combo.currentText()
            site_data = self.profiles.get(profile_name, {}).get("sites", {}).get(s)
            
            if site_data:
                # Si on a les infos, le bouton PMA affiche les identifiants
                btn_pma.clicked.connect(lambda *args, d=s, data=site_data: self.show_site_info(d, data))
                btn_pma.setStyleSheet("font-weight: bold; color: #2196F3;")
            else:
                # Sinon, il ouvre juste l'URL par défaut
                btn_pma.clicked.connect(self.open_phpmyadmin)
            
            btn_rename = QPushButton("🖊️")
            btn_rename.setFixedWidth(30)
            btn_rename.setToolTip("Renommer")
            btn_rename.clicked.connect(lambda *args, d=s: self.rename_site(d))

            row_layout.addWidget(icon_lbl)
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            
            row_layout.addWidget(btn_rename)
            row_layout.addWidget(btn_pma)
            row_layout.addWidget(btn_open)
            row_widget.setLayout(row_layout)
            
            item.setSizeHint(row_widget.sizeHint())
            self.site_list.setItemWidget(item, row_widget)

    def show_site_info(self, domain, data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Informations - {domain}")
        dialog.setFixedWidth(450)
        dialog.setFixedHeight(300)
        v_layout = QVBoxLayout(dialog)
        
        v_layout.addWidget(QLabel(f"<b>Identifiants pour {domain} :</b>"))
        
        info_text = f"Base de données : {data.get('db_name')}\n"
        info_text += f"Utilisateur     : {data.get('db_user')}\n"
        info_text += f"Mot de passe    : {data.get('db_pass')}\n"
        info_text += f"\nURL phpMyAdmin  : http://{self.host_input.text().strip()}/phpmyadmin/"
        
        text_area = QTextEdit()
        text_area.setPlainText(info_text)
        text_area.setReadOnly(True)
        text_area.setFont(QFont("Consolas", 10))
        # Styles pour la zone de texte
        text_area.setStyleSheet("background-color: #f4f4f4; border: 1px solid #ccc; padding: 10px;")
        v_layout.addWidget(text_area)
        
        btn_box = QHBoxLayout()
        pma_btn = QPushButton("Ouvrir phpMyAdmin")
        pma_btn.clicked.connect(lambda: [self.open_phpmyadmin(), dialog.accept()])
        copy_btn = QPushButton("Copier Mot de Passe")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(data.get('db_pass')))
        ok_btn = QPushButton("Fermer")
        ok_btn.clicked.connect(dialog.accept)
        
        btn_box.addWidget(pma_btn)
        btn_box.addWidget(copy_btn)
        btn_box.addWidget(ok_btn)
        v_layout.addLayout(btn_box)
        
        dialog.exec()

    def add_site(self):
        # Boîte de dialogue personnalisée pour inclure les options de DB
        dialog = QDialog(self)
        dialog.setWindowTitle("Nouveau Site")
        dialog_layout = QFormLayout(dialog)
        
        domain_input = QLineEdit()
        domain_input.setPlaceholderText("ex: monsite.com ou monsite")
        dialog_layout.addRow("Nom/Domaine :", domain_input)
        
        db_checkbox = QCheckBox("Créer une base de données MySQL")
        db_checkbox.setChecked(False)
        dialog_layout.addRow(db_checkbox)
        
        db_pass_input = QLineEdit()
        db_pass_input.setPlaceholderText("Mot de passe DB")
        db_pass_input.setEchoMode(QLineEdit.Password)
        db_pass_input.setEnabled(False)
        dialog_layout.addRow("Mot de passe DB :", db_pass_input)
        
        db_checkbox.toggled.connect(db_pass_input.setEnabled)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        dialog_layout.addRow(btns)
        
        if dialog.exec() != QDialog.Accepted:
            return
            
        domain = domain_input.text().strip()
        create_db = db_checkbox.isChecked()
        db_pass = db_pass_input.text().strip()
        
        if not domain: return
        
        base_domain = self.base_domain_input.text().strip()
        
        # Si on a pas de point mais qu'un base_domain est défini, on le concatène automatiquement
        if "." not in domain and base_domain:
            domain = f"{domain}.{base_domain}"
            
        doc_root = f"{BASE_DOCROOT}/{domain}"
        
        # Script de création amélioré avec ALIAS pour accès par IP
        cmds = [
            f"mkdir -p {doc_root}",
            f"echo '<h1>Projet {domain}</h1>' > {doc_root}/index.html",
            f"chown -R www-data:www-data {doc_root}",
            # Création du VirtualHost standard
            f"echo '<VirtualHost *:80>\nServerName {domain}\nDocumentRoot {doc_root}\n<Directory {doc_root}>\nAllowOverride All\nRequire all granted\n</Directory>\n</VirtualHost>' > /etc/apache2/sites-available/{domain}.conf",
            # Création de l'Alias pour l'accès IP/nom_du_projet
            f"echo 'Alias /{domain} {doc_root}\n<Directory {doc_root}>\nAllowOverride All\nRequire all granted\n</Directory>' > /etc/apache2/conf-available/{domain}-alias.conf",
            f"a2ensite {domain}.conf",
            f"a2enconf {domain}-alias",
            "systemctl reload apache2"
        ]
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for cmd in cmds: self.run_sudo_cmd(cmd)
        
        # Création de la DB si demandée
        if create_db and db_pass:
            # On nettoie le nom de la DB (pas de points)
            db_name = domain.replace(".", "_").replace("-", "_")
            
            # Sécurisation SQL et Shell
            # 1. Échappement des underscores pour le GRANT (MySQL les traite comme wildcards)
            db_name_escaped = db_name.replace("_", "\\_")
            # 2. Protection contre les injections SQL (doubler les quotes simples)
            db_pass_sql = db_pass.replace("'", "''")
            
            # Construction de la commande SQL
            sql = (
                f"CREATE DATABASE IF NOT EXISTS `{db_name}`; "
                f"CREATE USER IF NOT EXISTS '{db_name}'@'localhost' IDENTIFIED BY '{db_pass_sql}'; "
                f"GRANT ALL PRIVILEGES ON `{db_name_escaped}`.* TO '{db_name}'@'localhost'; "
                f"FLUSH PRIVILEGES;"
            )
            
            # shlex.quote assure que le shell distant reçoit exactement la chaîne SQL
            mysql_cmd = f"mysql -e {shlex.quote(sql)}"
            self.run_sudo_cmd(mysql_cmd)
            
            db_data = {"db_name": db_name, "db_user": db_name, "db_pass": db_pass}
            self.save_site_info(domain, db_data)
            db_info = f"\n\nBase de données : {db_name}\nUtilisateur : {db_name}\nMot de passe : {db_pass}"
        else:
            db_info = ""
        
        # Générer un certificat SSL s'il s'agit d'un domaine (présence d'un point)
        if "." in domain:
            self.run_sudo_cmd(f"certbot --apache -d {domain} --non-interactive --agree-tos --register-unsafely-without-email")
            
        QApplication.restoreOverrideCursor()
        self.list_sites()
        
        url_protocol = "https" if "." in domain else "http"
        url_display = f"{url_protocol}://{domain}" if "." in domain else f"http://{self.host_input.text()}/{domain}"
        QMessageBox.information(self, "Succès", f"Projet {domain} créé.\nAccès : {url_display}{db_info}")

    def rename_site(self, domain=None):
        if not domain:
            item = self.site_list.currentItem()
            if not item: 
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un site dans la liste.")
                return
            old_domain = item.data(Qt.UserRole)
        else:
            old_domain = domain
            
        profile_name = self.profile_combo.currentText()
        site_data = self.profiles.get(profile_name, {}).get("sites", {}).get(old_domain, {})
        old_db = site_data.get("db_name")

        # Boîte de dialogue pour le renommage
        dialog = QDialog(self)
        dialog.setWindowTitle("Renommer Site / DB")
        dialog_layout = QFormLayout(dialog)
        
        new_domain_input = QLineEdit(old_domain)
        dialog_layout.addRow("Nouveau nom site :", new_domain_input)
        
        db_rename_chk = QCheckBox("Renommer aussi la base de données")
        if not old_db:
            db_rename_chk.setEnabled(False)
        dialog_layout.addRow(db_rename_chk)
        
        new_db_input = QLineEdit(old_db if old_db else "")
        new_db_input.setEnabled(False)
        dialog_layout.addRow("Nouveau nom DB :", new_db_input)
        
        db_rename_chk.toggled.connect(new_db_input.setEnabled)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        dialog_layout.addRow(btns)
        
        if dialog.exec() != QDialog.Accepted:
            return
            
        new_domain = new_domain_input.text().strip()
        do_db_rename = db_rename_chk.isChecked()
        new_db = new_db_input.text().strip()
        
        if not new_domain or new_domain == old_domain:
            if not do_db_rename: return
            if do_db_rename and new_db == old_db: return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # 1. Renommage Apache et Répertoires (si le nom a changé)
        if new_domain != old_domain:
            self.log(f"Renommage du site: {old_domain} -> {new_domain}")
            old_doc_root = f"{BASE_DOCROOT}/{old_domain}"
            new_doc_root = f"{BASE_DOCROOT}/{new_domain}"
            
            cmds = [
                f"mv {old_doc_root} {new_doc_root}",
                f"mv /etc/apache2/sites-available/{old_domain}.conf /etc/apache2/sites-available/{new_domain}.conf",
                f"sed -i 's/{old_domain}/{new_domain}/g' /etc/apache2/sites-available/{new_domain}.conf",
                f"mv /etc/apache2/conf-available/{old_domain}-alias.conf /etc/apache2/conf-available/{new_domain}-alias.conf",
                f"sed -i 's/{old_domain}/{new_domain}/g' /etc/apache2/conf-available/{new_domain}-alias.conf",
                f"a2dissite {old_domain}.conf",
                f"a2disconf {old_domain}-alias",
                f"a2ensite {new_domain}.conf",
                f"a2enconf {new_domain}-alias",
                "systemctl reload apache2"
            ]
            for cmd in cmds: self.run_sudo_cmd(cmd)
            
            # Mise à jour metadata locale
            if old_domain in self.profiles[profile_name]["sites"]:
                self.profiles[profile_name]["sites"][new_domain] = self.profiles[profile_name]["sites"].pop(old_domain)

        # 2. Renommage Base de données (si demandé)
        if do_db_rename and old_db and new_db and new_db != old_db:
            self.log(f"Renommage DB: {old_db} -> {new_db}")
            # On utilise shlex.quote pour chaque commande
            db_rename_cmds = [
                f"mysqldump `{old_db}` > /tmp/{old_db}.sql",
                f"mysql -e {shlex.quote(f'CREATE DATABASE IF NOT EXISTS `{new_db}`;')}",
                f"mysql `{new_db}` < /tmp/{old_db}.sql",
                f"mysql -e {shlex.quote(f'DROP DATABASE `{old_db}`;')}",
                f"rm /tmp/{old_db}.sql"
            ]
            for cmd in db_rename_cmds: self.run_sudo_cmd(cmd)
            
            # Mise à jour des infos dans la metadata locale
            if new_domain in self.profiles[profile_name]["sites"]:
                self.profiles[profile_name]["sites"][new_domain]["db_name"] = new_db
                self.profiles[profile_name]["sites"][new_domain]["db_user"] = new_db # Simplification
                # On ne change pas le mot de passe pour l'instant pour éviter de casser les sites
                # mais l'utilisateur MySQL old_db devra être migré ou conservé.
                # Pour rester simple, on garde le même utilisateur MySQL (si on ne peut pas le renommer facilement).
                # Mais ici on affiche new_db comme utilisateur, donc on devrait le renommer.
                rename_sql = f"RENAME USER '{old_db}'@'localhost' TO '{new_db}'@'localhost';"
                self.run_sudo_cmd(f"mysql -e {shlex.quote(rename_sql)}")
                self.profiles[profile_name]["sites"][new_domain]["db_user"] = new_db
        
        # Sauvegarde finale config
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"profiles": self.profiles, "last_profile": profile_name}, f, indent=4)
        except: pass

        QApplication.restoreOverrideCursor()
        self.list_sites()
        QMessageBox.information(self, "Succès", f"Le site/DB a été renommé vers '{new_domain}'.")

    def remove_site(self):
        item = self.site_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un site dans la liste avant de cliquer sur Supprimer.")
            return
            
        domain = item.data(Qt.UserRole)
        
        # Confirmation de suppression
        confirm = QMessageBox.question(self, "Confirmer la suppression", 
            f"Voulez-vous vraiment supprimer le site '{domain}' ?\nCela supprimera les fichiers, la configuration Apache et la base de données associée.",
            QMessageBox.Yes | QMessageBox.No)
            
        if confirm != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Récupérer les infos DB avant de supprimer
            profile_name = self.profile_combo.currentText()
            site_data = self.profiles.get(profile_name, {}).get("sites", {}).get(domain, {})
            db_name = site_data.get("db_name")

            cmds = [
                f"a2dissite {domain}.conf",
                f"a2disconf {domain}-alias",
                f"rm -f /etc/apache2/sites-available/{domain}.conf",
                f"rm -f /etc/apache2/conf-available/{domain}-alias.conf",
                f"rm -rf {BASE_DOCROOT}/{domain}",
                "systemctl reload apache2"
            ]
            
            self.log(f"Suppression du site {domain}...")
            self.run_sudo_cmd(f"certbot delete --cert-name {domain} --non-interactive || true")
            for cmd in cmds: self.run_sudo_cmd(cmd)
            
            # Supprimer la DB si elle existe dans les métadonnées
            if db_name:
                self.log(f"Suppression de la base de données {db_name}...")
                sql_del = f"DROP DATABASE IF EXISTS `{db_name}`; DROP USER IF EXISTS '{db_name}'@'localhost';"
                mysql_del_cmd = f"mysql -e {shlex.quote(sql_del)}"
                self.run_sudo_cmd(mysql_del_cmd)
            
            # Supprimer aussi les infos du site dans le fichier config local
            if profile_name in self.profiles and "sites" in self.profiles[profile_name]:
                if domain in self.profiles[profile_name]["sites"]:
                    del self.profiles[profile_name]["sites"][domain]
                    with open(CONFIG_FILE, "w") as f:
                        json.dump({"profiles": self.profiles, "last_profile": profile_name}, f, indent=4)

            self.list_sites()
            QMessageBox.information(self, "Succès", f"Le site {domain} et sa base de données ont été supprimés.")
            
        except Exception as e:
            self.log(f"Erreur lors de la suppression: {e}")
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue lors de la suppression : {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def reload_apache(self):
        self.run_sudo_cmd("systemctl reload apache2")
        QMessageBox.information(self, "Info", "Apache rechargé")

    def open_site(self, domain=None, secure=None):
        if not domain:
            item = self.site_list.currentItem()
            if not item: return
            domain = item.data(Qt.UserRole)
            if not domain: return
            
        if secure is None:
            secure = ("." in domain)
            
        url = f"https://{domain}" if secure else f"http://{self.host_input.text().strip()}/{domain}/"
        if not secure and "." in domain:
            url = f"http://{domain}"
            
        webbrowser.open(url)

    def open_phpmyadmin(self):
        webbrowser.open(f"http://{self.host_input.text().strip()}/phpmyadmin")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ApacheManager()
    window.show()
    sys.exit(app.exec())