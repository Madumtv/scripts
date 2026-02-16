import sys
import paramiko
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

BASE_DOCROOT = "/var/www"

class ApacheManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apache VPS Manager")
        self.resize(700, 500)
        self.ssh_client = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # --- Connexion ---
        self.layout.addWidget(QLabel("Connexion au VPS Apache", alignment=Qt.AlignCenter))
        self.layout.addSpacing(10)

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

        self.connect_btn = QPushButton("Se connecter")
        self.connect_btn.clicked.connect(self.connect_ssh)
        self.layout.addWidget(self.connect_btn, alignment=Qt.AlignCenter)

        # --- Menu après connexion ---
        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout()
        self.menu_widget.setLayout(self.menu_layout)
        self.menu_widget.setVisible(False)  # Caché avant connexion

        # Liste des sites
        self.site_list = QListWidget()
        self.menu_layout.addWidget(QLabel("Sites disponibles :"))
        self.menu_layout.addWidget(self.site_list)

        # Boutons d'action
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter un site")
        self.add_btn.clicked.connect(self.add_site)
        self.remove_btn = QPushButton("Supprimer le site sélectionné")
        self.remove_btn.clicked.connect(self.remove_site)
        self.refresh_btn = QPushButton("Rafraîchir la liste")
        self.refresh_btn.clicked.connect(self.list_sites)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.refresh_btn)

        self.menu_layout.addLayout(btn_layout)
        self.layout.addWidget(self.menu_widget)

    # ---------------- SSH ----------------
    def connect_ssh(self):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        if not host or not user or not password:
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs !")
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(hostname=host, username=user, password=password)
            self.ssh_client = client
            QMessageBox.information(self, "Succès", f"Connexion réussie ! Bienvenue, {user}.")
            self.menu_widget.setVisible(True)
            self.connect_btn.setEnabled(False)
            self.list_sites()
        except Exception as e:
            QMessageBox.critical(self, "Erreur SSH", str(e))

    def run_cmd(self, cmd):
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        return stdout.read().decode(), stderr.read().decode()

    # ---------------- Liste ----------------
    def list_sites(self):
        if not self.ssh_client: return
        out, err = self.run_cmd("ls /etc/apache2/sites-available")
        if err:
            QMessageBox.warning(self, "Erreur", err)
            return
        self.site_list.clear()
        sites = set()
        for line in out.splitlines():
            site = line.replace(".conf", "").replace("-le-ssl", "")
            sites.add(site)
        for s in sorted(sites):
            self.site_list.addItem(s)

    # ---------------- Ajouter ----------------
    def add_site(self):
        from PySide6.QtWidgets import QInputDialog
        if not self.ssh_client: return
        domain, ok = QInputDialog.getText(self, "Ajouter site", "Nom du site (ex: nascarfan.madum.top):")
        if not ok or not domain.strip() or "." not in domain:
            return
        domain = domain.strip()
        doc_root = f"{BASE_DOCROOT}/{domain}"
        conf_file = f"{domain}.conf"
        cmds = [
            f"sudo mkdir -p {doc_root}",
            f"""echo '<!DOCTYPE html>
<html>
<head><title>{domain}</title></head>
<body>
<h1>Bienvenue sur {domain}</h1>
<p>Site créé avec le script Apache VPS GUI</p>
</body>
</html>' | sudo tee {doc_root}/index.html""",
            f"""echo '<VirtualHost *:80>
ServerName {domain}
DocumentRoot {doc_root}
<Directory {doc_root}>
AllowOverride All
Require all granted
</Directory>
ErrorLog ${{APACHE_LOG_DIR}}/{domain}_error.log
CustomLog ${{APACHE_LOG_DIR}}/{domain}_access.log combined
</VirtualHost>' | sudo tee /etc/apache2/sites-available/{conf_file}""",
            f"sudo a2ensite {conf_file}",
            "sudo systemctl reload apache2",
            f"sudo certbot --apache -d {domain} --non-interactive"
        ]
        for cmd in cmds:
            self.run_cmd(cmd)
        QMessageBox.information(self, "Succès", f"Site {domain} créé !")
        self.list_sites()

    # ---------------- Supprimer ----------------
    def remove_site(self):
        if not self.ssh_client: return
        item = self.site_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un site à supprimer.")
            return
        domain = item.text()
        conf_file = f"{domain}.conf"
        doc_root = f"{BASE_DOCROOT}/{domain}"
        cmds = [
            f"sudo a2dissite {conf_file}",
            "sudo systemctl reload apache2",
            f"sudo rm /etc/apache2/sites-available/{conf_file}",
            f"sudo rm -rf {doc_root}",
            f"sudo certbot delete --cert-name {domain} --non-interactive"
        ]
        for cmd in cmds:
            self.run_cmd(cmd)
        QMessageBox.information(self, "Succès", f"Site {domain} supprimé !")
        self.list_sites()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = ApacheManager()
    window.show()
    sys.exit(app.exec())
