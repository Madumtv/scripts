import http.server
import socketserver
import os
import sys

# Mini serveur pour exécuter des commandes locales depuis le Dashboard
# ATTENTION : Ne lancer que sur localhost (127.0.0.1)

PORT = 8080

class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Sécurité : On ne lance que les scripts autorisés du workflow
        authorized_cmds = ['./init-workspace.ps1', './create-skill.ps1', 'Pousser sur GitHub', 'Déploie sur GitHub Pages']
        
        if any(cmd in post_data for cmd in authorized_cmds):
            print(f"[BRIDGE] Exécution de : {post_data}")
            # On écrit la commande dans un fichier log que l'IA surveille ou on l'affiche simplement
            # Pour l'instant on se contente de logger le succès du clic
            self.wfile.write(b"Action recue par le Bridge")
        else:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Commande non autorisee")

with socketserver.TCPServer(("127.0.0.1", PORT), BridgeHandler) as httpd:
    print(f"[BRIDGE] Serveur actif sur http://127.0.0.1:{PORT}")
    httpd.serve_forever()
