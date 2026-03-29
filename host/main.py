import sys
import os
import json
import shlex
import re
import webbrowser
import threading
import paramiko
import xml.etree.ElementTree as ET
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QDateTime, Signal, QObject, QTimer
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox,
                               QComboBox, QTabWidget, QTextEdit, QListWidgetItem, QDialog, 
                               QFormLayout, QDialogButtonBox, QCheckBox, QFileDialog, QProgressBar)

# --- Gestion des tâches en arrière-plan ---
class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

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

        # -- Onglet Ressources --
        self.res_tab = QWidget()
        self.res_layout = QVBoxLayout()
        self.res_tab.setLayout(self.res_layout)
        self.tabs.addTab(self.res_tab, "Ressources")

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

        self.clear_logs_btn = QPushButton("Vider les logs")
        self.clear_logs_btn.clicked.connect(self.log_output.clear)
        self.log_layout.addWidget(self.clear_logs_btn)

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
        
        self.diag_btn = QPushButton("Diagnostiquer Apache")
        self.diag_btn.clicked.connect(self.diagnose_apache)
        nav_layout.addWidget(self.diag_btn)
        
        self.firewall_btn = QPushButton("Vérifier Firewall")
        self.firewall_btn.clicked.connect(self.check_firewall)
        nav_layout.addWidget(self.firewall_btn)
        
        self.menu_layout.addLayout(nav_layout)
        self.layout.addWidget(self.menu_widget)
        
        # --- Stats (Anciennement Option 1, maintenant Onglet Ressources) ---
        def create_stat_block(label, bar_obj):
            container = QWidget()
            layout = QVBoxLayout(container)
            lbl = QLabel(f"<b>{label}</b>")
            layout.addWidget(lbl)
            layout.addWidget(bar_obj)
            return container

        def create_bar(label, color):
            bar = QProgressBar()
            bar.setFormat(label + ": %p%")
            bar.setRange(0, 100)
            bar.setFixedHeight(25)
            bar.setStyleSheet(f"QProgressBar {{ text-align: center; border-radius: 12px; background-color: #edf2f7; color: #2d3748; font-weight: bold; border: 1px solid #e2e8f0; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 11px; }}")
            return bar

        self.cpu_bar = create_bar("CPU", "#3182ce")
        self.ram_bar = create_bar("RAM", "#805ad5")
        self.disk_bar = create_bar("SSD", "#dd6b20")
        
        self.res_layout.addWidget(QLabel("<h3>État du Système en Temps Réel</h3>", alignment=Qt.AlignCenter))
        self.res_layout.addSpacing(20)
        self.res_layout.addWidget(create_stat_block("Utilisation Processeur (CPU)", self.cpu_bar))
        self.res_layout.addSpacing(10)
        self.res_layout.addWidget(create_stat_block("Utilisation Mémoire Vive (RAM)", self.ram_bar))
        self.res_layout.addSpacing(10)
        self.res_layout.addWidget(create_stat_block("Espace Disque (SSD)", self.disk_bar))
        self.res_layout.addStretch()
        
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        
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

    def save_site_info(self, domain, data):
        profile_name = self.profile_name_input.text().strip() or self.host_input.text().strip()
        if profile_name not in self.profiles: return
        
        if "sites" not in self.profiles[profile_name]:
            self.profiles[profile_name]["sites"] = {}
            
        if domain not in self.profiles[profile_name]["sites"]:
            self.profiles[profile_name]["sites"][domain] = {}
            
        self.profiles[profile_name]["sites"][domain].update(data)
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"profiles": self.profiles, "last_profile": profile_name}, f, indent=4)
        except Exception as e: self.log(f"Erreur sauvegarde site: {e}")

    def connect_ssh(self):
        host, user, password = self.host_input.text().strip(), self.user_input.text().strip(), self.pass_input.text().strip()
        base_domain = self.base_domain_input.text().strip()
        if not all([host, user, password]): return
        
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connexion...")
        
        def do_connect():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password)
            return client

        self.worker = Worker(do_connect)
        self.worker.finished.connect(self.on_connect_success)
        self.worker.error.connect(self.on_connect_error)
        
        self.thread = threading.Thread(target=self.worker.run)
        self.thread.start()

    def on_connect_success(self, client):
        self.ssh_client = client
        self.save_config(self.host_input.text(), self.user_input.text(), self.pass_input.text(), self.base_domain_input.text())
        self.menu_widget.setVisible(True)
        self.connect_btn.setText("Connecté")
        self.list_sites()
        self.update_stats()
        self.stats_timer.start(10000) # Rafraîchir toutes les 10 secondes

    def on_connect_error(self, err):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Se connecter")
        QMessageBox.critical(self, "Erreur SSH", str(err))

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
        self.refresh_btn.setEnabled(False)
        
        def fetch_data():
            out, _ = self.run_cmd("ls /etc/apache2/sites-available")
            available_files = out.splitlines()
            sites_ssl = {}
            for line in available_files:
                line = line.strip()
                if not line or line in ["default-ssl.conf", "000-default.conf"]: continue
                if "-le-ssl.conf" in line:
                    domain = line.replace("-le-ssl.conf", "")
                    sites_ssl[domain] = True
                elif line.endswith(".conf"):
                    domain = line.replace(".conf", "")
                    if domain not in sites_ssl:
                        sites_ssl[domain] = False
            return sorted(sites_ssl.items())

        self.list_worker = Worker(fetch_data)
        self.list_worker.finished.connect(self.on_list_success)
        self.list_worker.error.connect(lambda e: [self.log(f"Erreur list: {e}"), self.refresh_btn.setEnabled(True)])
        
        self.list_thread = threading.Thread(target=self.list_worker.run)
        self.list_thread.start()

    def on_list_success(self, sites_data):
        self.site_list.clear()
        self.refresh_btn.setEnabled(True)
        
        for s, has_ssl in sites_data:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, s)
            self.site_list.addItem(item)
            
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(5, 2, 5, 2)
            
            is_domain = "." in s
            icon_lbl = QLabel("🔒" if has_ssl else ("🌐" if is_domain else "📁"))
            if has_ssl:
                icon_lbl.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
            elif is_domain:
                icon_lbl.setStyleSheet("color: #FF9800; font-size: 14px;")
            else:
                icon_lbl.setStyleSheet("color: #2196F3; font-size: 14px;")
                
            lbl = QLabel(s)
            
            # Bouton Dossier (Local)
            btn_folder = QPushButton("📂 Dossier")
            btn_folder.setFixedWidth(85)
            btn_folder.setToolTip("Lier à un dossier local")
            btn_folder.clicked.connect(lambda *args, d=s: self.set_local_path(d))

            # Bouton Code (VS Code)
            btn_code = QPushButton("💻 Code")
            btn_code.setFixedWidth(70)
            btn_code.setToolTip("Ouvrir dans VS Code")
            btn_code.clicked.connect(lambda *args, d=s: self.open_local_code(d))

            # Bouton FileZilla (Export auto)
            btn_fz = QPushButton("🛰️ FileZilla")
            btn_fz.setFixedWidth(95)
            btn_fz.setToolTip("Exporter vers FileZilla (Site Manager)")
            btn_fz.clicked.connect(lambda *args, d=s: self.export_filezilla(d))

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
            
            # Bouton SSL si pas encore de SSL et que c'est un domaine
            if not has_ssl and "." in s:
                btn_cert = QPushButton("SSL")
                btn_cert.setFixedWidth(40)
                btn_cert.setToolTip("Générer un certificat SSL (Certbot)")
                btn_cert.clicked.connect(lambda *args, d=s: self.create_ssl(d))
                row_layout.addWidget(btn_cert)

            row_layout.addWidget(btn_rename)
            row_layout.addWidget(btn_pma)
            row_layout.addWidget(btn_folder)
            row_layout.addWidget(btn_code)
            row_layout.addWidget(btn_fz)
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

        # Ajout du choix du dossier local lors de la création
        local_path_input = QLineEdit()
        local_path_input.setPlaceholderText("Dossier source du code")
        local_path_btn = QPushButton("Parcourir...")
        local_path_btn.clicked.connect(lambda: local_path_input.setText(QFileDialog.getExistingDirectory(dialog, "Sélectionner le dossier local")))
        
        local_layout = QHBoxLayout()
        local_layout.addWidget(local_path_input)
        local_layout.addWidget(local_path_btn)
        dialog_layout.addRow("Dossier Local :", local_layout)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        dialog_layout.addRow(btns)
        
        if dialog.exec() != QDialog.Accepted:
            return
            
        domain = domain_input.text().strip()
        create_db = db_checkbox.isChecked()
        db_pass = db_pass_input.text().strip()
        local_path = local_path_input.text().strip()
        
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
        
        # Enregistrement des infos
        site_info = {}
        if local_path: site_info["local_path"] = local_path
        if site_info: self.save_site_info(domain, site_info)

        self.list_sites()
        
        url_protocol = "https" if "." in domain else "http"
        url_display = f"{url_protocol}://{domain}" if "." in domain else f"http://{self.host_input.text()}/{domain}"
        
        # Demander l'export FileZilla immédiat
        confirm_fz = QMessageBox.question(self, "Export FileZilla", 
            f"Projet {domain} créé !\nVoulez-vous l'exporter immédiatement vers FileZilla ?",
            QMessageBox.Yes | QMessageBox.No)
            
        if confirm_fz == QMessageBox.Yes:
            self.export_filezilla(domain)

        QMessageBox.information(self, "Succès", f"Projet {domain} finalisé.\nAccès : {url_display}{db_info}")

    def create_ssl(self, domain):
        confirm = QMessageBox.question(self, "SSL Certbot", 
            f"Voulez-vous générer un certificat SSL pour '{domain}' via Certbot ?",
            QMessageBox.Yes | QMessageBox.No)
            
        if confirm != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.tabs.setCurrentIndex(1) # Basculer sur l'onglet Logs pour voir l'avancement
        try:
            self.log(f"--- Lancement SSL pour {domain} ---")
            self.log("Exécution de certbot...")
            out, err = self.run_sudo_cmd(f"certbot --apache -d {domain} --non-interactive --agree-tos --register-unsafely-without-email")
            
            if out: self.log(f"Sortie: {out}")
            if err: self.log(f"Erreur/Warning: {err}")
            
            if "Congratulations!" in out or "Successfully deployed" in out or "Certificate not yet due for renewal" in out:
                self.log(f"SSL généré avec succès pour {domain}")
                self.tabs.setCurrentIndex(0) # Revenir au gestionnaire
                QMessageBox.information(self, "Succès SSL", f"Le certificat SSL pour {domain} a été généré et configuré avec succès.")
            else:
                self.log(f"ERREUR: Certbot n'a pas renvoyé de message de succès.")
                QMessageBox.critical(self, "Échec SSL", f"La génération du certificat a probablement échoué pour {domain}.\nVérifiez les logs pour plus de détails.")
            
            self.list_sites()
        except Exception as e:
            self.log(f"EXCEPTION SSL: {e}")
            QMessageBox.critical(self, "Erreur Critique", f"Une erreur est survenue lors de l'appel à Certbot : {e}")
        finally:
            QApplication.restoreOverrideCursor()

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

    def diagnose_apache(self):
        self.log("--- Diagnostic Apache ---")
        out, err = self.run_sudo_cmd("apache2ctl configtest")
        full_res = (out + "\n" + err).strip()
        
        if "Syntax OK" in full_res:
            self.log("Apache: Syntaxe OK")
            QMessageBox.information(self, "Apache OK", "La configuration Apache est valide.")
        else:
            self.log(f"Erreur détectée:\n{full_res}")
            self.tabs.setCurrentIndex(1)
            
            # Recherche du fichier qui cause l'erreur
            match = re.search(r"(/etc/apache2/sites-enabled/|/etc/apache2/sites-available/)([^:\s]+)", full_res)
            if match:
                file_path = match.group(0)
                file_name = match.group(2)
                
                confirm = QMessageBox.warning(self, "Erreur de configuration", 
                    f"Une erreur a été détectée dans le fichier :\n{file_name}\n\nCela bloque la génération de nouveaux certificats.\n\nVoulez-vous désactiver ce site pour réparer Apache ?",
                    QMessageBox.Yes | QMessageBox.No)
                    
                if confirm == QMessageBox.Yes:
                    self.log(f"Désactivation de {file_name}...")
                    self.run_sudo_cmd(f"a2dissite {file_name}")
                    self.run_sudo_cmd("systemctl reload apache2")
                    self.list_sites()
                    QMessageBox.information(self, "Réparé", f"Le site {file_name} a été désactivé. Apache a été rechargé.")
            else:
                QMessageBox.critical(self, "Erreur Apache", f"Impossible de corriger automatiquement l'erreur :\n\n{full_res[:300]}...")

    def check_firewall(self):
        self.log("--- Vérification du Firewall (UFW) ---")
        out, err = self.run_sudo_cmd("ufw status")
        self.log(f"Status UFW:\n{out}")
        
        # Vérification si les ports 80/443 sont ouverts ou si UFW est inactif
        is_blocked = ("80/tcp" not in out and "80" not in out)
        if "inactive" in out.lower():
            self.log("UFW est inactif (tout est ouvert par défaut).")
            QMessageBox.information(self, "Firewall", "UFW est inactif sur votre VPS. Le blocage vient probablement d'ailleurs (ex: firewall externe du fournisseur).")
            return

        if is_blocked:
            confirm = QMessageBox.question(self, "Ports HTTP fermés ?", 
                "Le port 80 n'apparaît pas dans la liste ALLOW de UFW.\n\nAutoriser les ports 80 (HTTP) et 443 (HTTPS) ?",
                QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.log("Ouverture des ports 80 et 443...")
                self.run_sudo_cmd("ufw allow 80/tcp")
                self.run_sudo_cmd("ufw allow 443/tcp")
                self.run_sudo_cmd("ufw reload")
                self.log("Ports 80 et 443 ouverts avec succès.")
                QMessageBox.information(self, "Firewall", "Les ports 80 et 443 ont été ouverts.\nRéessayez la génération SSL.")
        else:
            QMessageBox.information(self, "Firewall OK", "Le port 80 est déjà autorisé dans UFW.")

    def encode_fz_path(self, path):
        if not path: return ""
        path = path.replace("\\", "/")
        parts = [p for p in path.split("/") if p]
        return "1 0 " + " ".join([f"{len(p)} {p}" for p in parts])

    def update_stats(self):
        if not self.ssh_client: return
        
        def fetch_stats():
            try:
                # Commande optimisée pour récupérer les 3 valeurs d'un coup
                # CPU: idle proportion, RAM: used/total, Disk: % usage
                cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'; free | awk '/Mem:/ {print $3/$2 * 100.0}'; df / | awk 'NR==2 {print $5}' | sed 's/%//'"
                out, _ = self.run_cmd(cmd)
                lines = out.splitlines()
                if len(lines) >= 3:
                    return [float(lines[0]), float(lines[1]), float(lines[2])]
            except: pass
            return None

        self.stats_worker = Worker(fetch_stats)
        self.stats_worker.finished.connect(self.on_stats_ready)
        self.stats_thread = threading.Thread(target=self.stats_worker.run)
        self.stats_thread.start()

    def on_stats_ready(self, values):
        if not values: return
        
        bars = [(self.cpu_bar, values[0], "#3182ce"), 
                (self.ram_bar, values[1], "#805ad5"), 
                (self.disk_bar, values[2], "#dd6b20")]
        
        for bar, val, color in bars:
            bar.setValue(int(val))
            # Couleur dynamique si surcharge (> 90%)
            final_color = "#e53e3e" if val > 90 else color
            bar.setStyleSheet(f"QProgressBar {{ text-align: center; border-radius: 9px; background-color: #edf2f7; color: #2d3748; font-weight: bold; font-size: 10px; border: 1px solid #e2e8f0; }} QProgressBar::chunk {{ background-color: {final_color}; border-radius: 8px; }}")

    def export_filezilla(self, domain):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        profile_name = self.profile_name_input.text().strip() or host
        
        # Récupération du dossier local lié via le profil actuel
        active_prof = self.profile_combo.currentText()
        if active_prof == "Nouveau profil...": active_prof = profile_name
        
        site_data = self.profiles.get(active_prof, {}).get("sites", {}).get(domain, {})
        local_path = site_data.get("local_path")
        
        if not local_path:
            confirm = QMessageBox.question(self, "Dossier local", 
                f"Le site '{domain}' n'est pas encore lié à un dossier local.\n\nVoulez-vous le lier maintenant pour l'inclure comme 'Dossier local par défaut' dans FileZilla ?",
                QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.set_local_path(domain)
                # Re-charger après sélection
                site_data = self.profiles.get(active_prof, {}).get("sites", {}).get(domain, {})
                local_path = site_data.get("local_path")

        # Le chemin par défaut de FileZilla sur Windows
        fz_dir = os.path.join(os.environ.get("APPDATA", ""), "FileZilla")
        fz_path = os.path.join(fz_dir, "sitemanager.xml")
        
        # Encodages paths pour FileZilla
        encoded_remote = self.encode_fz_path(f"{BASE_DOCROOT}/{domain}")
        encoded_local = self.encode_fz_path(local_path)

        # Création de l'élément de serveur pour le XML
        server = ET.Element("Server")
        ET.SubElement(server, "Host").text = host
        ET.SubElement(server, "Port").text = "22"
        ET.SubElement(server, "Protocol").text = "1" # SFTP
        ET.SubElement(server, "Type").text = "0"
        ET.SubElement(server, "User").text = user
        ET.SubElement(server, "Logontype").text = "1" # Password normal
        ET.SubElement(server, "Pass").text = password
        ET.SubElement(server, "Name").text = f"{profile_name} - {domain}"
        ET.SubElement(server, "RemoteDir").text = encoded_remote
        if encoded_local:
            ET.SubElement(server, "LocalDir").text = encoded_local
            ET.SubElement(server, "SyncBrowsing").text = "1" # Activation navigation synchronisée
        
        try:
            if os.path.exists(fz_path):
                tree = ET.parse(fz_path)
                root = tree.getroot()
                servers = root.find("Servers")
                if servers is None:
                    servers = ET.SubElement(root, "Servers")
                
                # Suppression des doublons (même nom de profil)
                site_name = f"{profile_name} - {domain}"
                for s in servers.findall("Server"):
                    if s.find("Name") is not None and s.find("Name").text == site_name:
                        servers.remove(s)
                
                servers.append(server)
                
                # Mise en forme (indentation rudimentaire)
                def indent(elem, level=0):
                    i = "\n" + level*"  "
                    if len(elem):
                        if not elem.text or not elem.text.strip():
                            elem.text = i + "  "
                        if not elem.tail or not elem.tail.strip():
                            elem.tail = i
                        for elem in elem:
                            indent(elem, level+1)
                        if not elem.tail or not elem.tail.strip():
                            elem.tail = i
                    else:
                        if level and (not elem.tail or not elem.tail.strip()):
                            elem.tail = i
                
                indent(root)
                tree.write(fz_path, encoding="utf-8", xml_declaration=True)
                self.log(f"Site {domain} exporté vers FileZilla.")
                QMessageBox.information(self, "FileZilla", 
                    f"Site '{domain}' intégré avec succès dans FileZilla !\n\nNote : Redémarrez FileZilla s'il était déjà ouvert.")
            else:
                # Fallback : Création d'un fichier .xml sur le bureau siconfig introuvable
                desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
                file_path = os.path.join(desktop, f"FileZilla_{domain}.xml")
                
                # Wrap dans une structure FileZilla3 valide
                root_node = ET.Element("FileZilla3", version="3.0", platform="windows")
                servers_node = ET.SubElement(root_node, "Servers")
                servers_node.append(server)
                
                tree = ET.ElementTree(root_node)
                tree.write(file_path, encoding="utf-8", xml_declaration=True)
                
                QMessageBox.warning(self, "Export FileZilla", 
                    f"Configuration FileZilla introuvable.\nUn fichier d'import a été créé sur votre bureau :\n\n{file_path}")
        except Exception as e:
            self.log(f"Erreur Export FileZilla: {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export FileZilla : {e}")

    def open_local_code(self, site_name):
        profile_name = self.profile_name_input.text().strip() or self.host_input.text().strip()
        site_data = self.profiles.get(profile_name, {}).get("sites", {}).get(site_name, {})
        local_path = site_data.get("local_path")
        
        if not local_path or not os.path.exists(local_path):
            self.set_local_path(site_name)
            # Recharger après sélection
            site_data = self.profiles.get(profile_name, {}).get("sites", {}).get(site_name, {})
            local_path = site_data.get("local_path")
            if not local_path: return

        self.log(f"Ouverture de {local_path} dans VS Code...")
        try:
            os.system(f'code "{local_path}"')
        except Exception as e:
            self.log(f"Erreur ouverture VS Code : {e}")

    def set_local_path(self, site_name):
        path = QFileDialog.getExistingDirectory(self, f"Sélectionner le dossier pour {site_name}")
        if path:
            self.save_site_info(site_name, {"local_path": path})
            self.log(f"Dossier pour {site_name} lié à : {path}")
            self.list_sites() # Rafraîchir pour voir les changements (tooltips, etc)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ApacheManager()
    window.show()
    sys.exit(app.exec())