import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime

def validate_date(date_str):
    """Valide que la date est au format YYYY-MM-DD et dans le futur."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if date_obj <= datetime.now():
            return False, "La date de fin de garantie doit être dans le futur."
        return True, ""
    except ValueError:
        return False, "La date de fin de garantie doit être au format YYYY-MM-DD."


class Database:
    """Classe pour gérer la base de données MySQL."""

    def __init__(self, host="localhost", port=3306, user="root", password="root", database="gestion_de_parc"):
        """Initialise la connexion à la base de données MySQL."""
        self.conn = None
        self.cursor = None
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        try:
            self.conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.conn.cursor(dictionary=True)
            self._ensure_tables()
        except Error as err:
            messagebox.showerror("Erreur connexion BDD",
                                 f"Impossible de se connecter : {err}")

    def _ensure_tables(self):
        """Crée les tables si elles n'existent pas encore."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipement (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nom VARCHAR(255) NOT NULL,
                numSerie VARCHAR(255),
                dateFinGarantie DATE,
                etat VARCHAR(100),
                id_salle INT,
                id_type_equipement VARCHAR(100)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS intervention (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_equipement INT NOT NULL,
                date_intervention DATE NOT NULL,
                type_action VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                technicien VARCHAR(100) NOT NULL,
                FOREIGN KEY (id_equipement) REFERENCES equipement(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def is_connected(self):
        """Vérifie si la connexion à la DB est active."""
        return self.conn is not None and self.cursor is not None

    def fetch(self, table):
        """Récupère toutes les données d'une table."""
        if not self.is_connected():
            messagebox.showerror("Erreur", "Pas connecté à la base de données.")
            return []

        try:
            self.cursor.execute(f"SELECT * FROM {table}")
            return self.cursor.fetchall()
        except Error as err:
            messagebox.showerror("Erreur SQL", str(err))
            return []

    def execute(self, query, params=None):
        """Exécute une requête SQL."""
        if not self.is_connected():
            messagebox.showerror("Erreur", "Pas connecté à la base de données.")
            return

        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
        except Error as err:
            messagebox.showerror("Erreur SQL", str(err))


class Application(tk.Tk):
    """Classe principale de l'application GUI pour gérer le parc informatique."""

    def __init__(self):
        super().__init__()

        self.title("Gestion de Parc Informatique")
        self.geometry("900x500")
        self.db = Database()
        self.build_ui()
        self.update_idletasks()  # Force la mise à jour des widgets avant utilisation
        self.load_equipements()

    def build_ui(self):
        """Construit l'interface utilisateur."""
        title = tk.Label(self, text="Liste des Équipements",
                         font=("Arial", 18, "bold"))
        title.pack(pady=10)

        # Barre de recherche
        search_frame = tk.Frame(self)
        search_frame.pack(pady=5)

        tk.Label(search_frame, text="Rechercher par :").grid(row=0, column=0, padx=5)
        self.search_criteria = ttk.Combobox(search_frame, values=["Salle", "Type équipement", "Nom", "Numéro de série", "État"], state='readonly')
        self.search_criteria.grid(row=0, column=1, padx=5)
        self.search_criteria.current(0)  # Défaut : Salle

        tk.Label(search_frame, text="Valeur :").grid(row=0, column=2, padx=5)
        self.search_entry = tk.Entry(search_frame)
        self.search_entry.grid(row=0, column=3, padx=5)

        tk.Button(search_frame, text="Rechercher", command=self.search_equipements).grid(row=0, column=4, padx=5)
        tk.Button(search_frame, text="Tout afficher", command=self.load_equipements).grid(row=0, column=5, padx=5)

        # Tableau TreeView
        self.tree = ttk.Treeview(
            self,
            columns=("id", "nom", "numSerie", "dateFinGarantie", "etat",
                     "id_salle", "id_type_equipement"),
            show="headings"
        )

        columns_names = [
            ("id", "ID"),
            ("nom", "Nom"),
            ("numSerie", "Numéro de série"),
            ("dateFinGarantie", "Fin de garantie"),
            ("etat", "État"),
            ("id_salle", "Salle"),
            ("id_type_equipement", "Type équipement")
        ]

        for col, text in columns_names:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=120)

        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Ajouter", width=15,
                  command=self.add_equipment).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Modifier", width=15,
                  command=self.edit_equipment).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Supprimer", width=15,
                  command=self.delete_equipment).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Interventions", width=15,
                  command=self.show_interventions).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Rafraîchir", width=15,
                  command=self.load_equipements).grid(row=0, column=4, padx=5)

    def search_equipements(self):
        """Recherche les équipements selon le critère et la valeur sélectionnés."""
        criteria = self.search_criteria.get()
        value = self.search_entry.get().strip()

        if not value:
            messagebox.showwarning("Attention", "Veuillez entrer une valeur de recherche.")
            return

        # Mapping des critères vers les noms de colonnes SQL
        criteria_map = {
            "Salle": "id_salle",
            "Type équipement": "id_type_equipement",
            "Nom": "nom",
            "Numéro de série": "numSerie",
            "État": "etat"
        }

        column = criteria_map.get(criteria)
        if not column:
            return

        # Pour Salle, on cherche un ID numérique
        if criteria == "Salle":
            if not value.isdigit():
                messagebox.showerror("Erreur", "L'ID de salle doit être un nombre.")
                return
            filter_query = f"{column} = %s"
            filter_params = [value]
        else:
            filter_query = f"{column} LIKE %s"
            filter_params = [f"%{value}%"]

        self.load_equipements(filter_query, filter_params)

    def load_equipements(self, filter_query=None, filter_params=None):
        """Charge les équipements dans le tableau, avec un filtre optionnel."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        if filter_query:
            query = f"SELECT * FROM equipement WHERE {filter_query}"
            params = filter_params or []
        else:
            query = "SELECT * FROM equipement"
            params = []

        try:
            self.cursor = self.db.conn.cursor(dictionary=True)
            self.cursor.execute(query, params)
            data = self.cursor.fetchall()
        except Error as err:
            messagebox.showerror("Erreur SQL", str(err))
            return

        for item in data:
            self.tree.insert("", tk.END, values=(
                item["id"],
                item["nom"],
                item["numSerie"],
                item["dateFinGarantie"],
                item["etat"],
                item["id_salle"],
                item["id_type_equipement"]
            ))

    def add_equipment(self):
        """Ouvre une fenêtre pour ajouter un nouvel équipement."""
        win = tk.Toplevel(self)
        win.title("Ajouter un équipement")
        tk.Label(win, text="Nom :").grid(row=0, column=0, padx=10, pady=5)
        entry_nom = tk.Entry(win)
        entry_nom.grid(row=0, column=1, padx=10, pady=5)
        tk.Label(win, text="Numéro de série :").grid(row=1, column=0, padx=10, pady=5)
        entry_numSerie = tk.Entry(win)
        entry_numSerie.grid(row=1, column=1, padx=10, pady=5)
        tk.Label(win, text="Fin de garantie :").grid(row=2, column=0, padx=10, pady=5)
        entry_dateFinGarantie = tk.Entry(win)
        entry_dateFinGarantie.grid(row=2, column=1, padx=10, pady=5)
        tk.Label(win, text="État :").grid(row=3, column=0, padx=10, pady=5)
        etat_options = ["Parfait état", "Bon état", "État médiocre", "Mauvais état"]
        entry_etat = ttk.Combobox(win, values=etat_options, state='readonly')
        entry_etat.grid(row=3, column=1, padx=10, pady=5)
        entry_etat.current(0)

        tk.Label(win, text="ID Salle :").grid(row=4, column=0, padx=10, pady=5)
        entry_id_salle = tk.Entry(win)
        entry_id_salle.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(win, text="ID Type Équipement :").grid(row=5, column=0, padx=10, pady=5)
        type_options = ["Portable", "Poste de travail", "Imprimante", "NAS", "Serveur"]
        entry_id_type_equipement = ttk.Combobox(win, values=type_options, state='readonly')
        entry_id_type_equipement.grid(row=5, column=1, padx=10, pady=5)
        entry_id_type_equipement.current(0)

        type_map = {
            "Portable": "Portable",
            "Poste de travail": "Poste de travail",
            "Imprimante": "Imprimante",
            "NAS": "NAS",
            "Serveur": "Serveur"
        }

        def validate():
            nom = entry_nom.get().strip()
            numSerie = entry_numSerie.get().strip()
            dateFinGarantie = entry_dateFinGarantie.get().strip()
            etat = entry_etat.get().strip()
            id_salle = entry_id_salle.get().strip()
            id_type_equipement = entry_id_type_equipement.get().strip()

            if not nom:
                messagebox.showerror("Erreur", "Le nom est obligatoire.")
                return
            
            if not numSerie:
                messagebox.showerror("Erreur", "Le numéro de série est obligatoire.")
                return
            
            if not dateFinGarantie:
                messagebox.showerror("Erreur", "La date de fin de garantie est obligatoire.")
                return

            is_valid, error_msg = validate_date(dateFinGarantie)
            if not is_valid:
                messagebox.showerror("Erreur", error_msg)
                return

            if etat not in etat_options:
                messagebox.showerror("Erreur", "Choisir un état valide.")
                return
            
            if not id_salle:
                messagebox.showerror("Erreur", "L'ID de salle est obligatoire.")
                return

            if id_type_equipement not in type_map:
                messagebox.showerror("Erreur", "Choisir un type d'équipement valide.")
                return

            id_type_equipement_val = type_map[id_type_equipement]

            self.db.execute("""
                INSERT INTO equipement (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement_val))

            self.load_equipements()
            win.destroy()
        tk.Button(win, text="Ajouter", command=validate).grid(row=6, column=0, columnspan=2, pady=10)

    def edit_equipment(self):
        """Ouvre une fenêtre pour modifier un équipement existant."""
        win = tk.Toplevel(self)
        win.title("Modifier un équipement")

        # Champ ID
        tk.Label(win, text="ID de l'équipement :").grid(row=0, column=0, padx=10, pady=5)
        entry_id = tk.Entry(win)
        entry_id.grid(row=0, column=1, padx=10, pady=5)

        # Champs pour modification
        tk.Label(win, text="Nom :").grid(row=1, column=0, padx=10, pady=5)
        entry_nom = tk.Entry(win)
        entry_nom.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(win, text="Numéro de série :").grid(row=2, column=0, padx=10, pady=5)
        entry_numSerie = tk.Entry(win)
        entry_numSerie.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(win, text="Fin de garantie :").grid(row=3, column=0, padx=10, pady=5)
        entry_dateFinGarantie = tk.Entry(win)
        entry_dateFinGarantie.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(win, text="État :").grid(row=4, column=0, padx=10, pady=5)
        etat_options = ["Parfait état", "Bon état", "État médiocre", "Mauvais état"]
        entry_etat = ttk.Combobox(win, values=etat_options, state='readonly')
        entry_etat.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(win, text="ID Salle :").grid(row=5, column=0, padx=10, pady=5)
        entry_id_salle = tk.Entry(win)
        entry_id_salle.grid(row=5, column=1, padx=10, pady=5)

        tk.Label(win, text="Type Équipement :").grid(row=6, column=0, padx=10, pady=5)
        type_options = ["Portable", "Poste de travail", "Imprimante", "NAS", "Serveur"]
        entry_id_type_equipement = ttk.Combobox(win, values=type_options, state='readonly')
        entry_id_type_equipement.grid(row=6, column=1, padx=10, pady=5)

        def load_data():
            id_to_load = entry_id.get().strip()
            if not id_to_load.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre.")
                return
            data = self.db.fetch("equipement")
            item = None
            for row in data:
                if str(row["id"]) == id_to_load:
                    item = row
                    break
            if not item:
                messagebox.showerror("Erreur", "Équipement non trouvé.")
                return
            entry_nom.delete(0, tk.END)
            entry_nom.insert(0, item["nom"])
            entry_numSerie.delete(0, tk.END)
            entry_numSerie.insert(0, item["numSerie"])
            entry_dateFinGarantie.delete(0, tk.END)
            entry_dateFinGarantie.insert(0, item["dateFinGarantie"])
            entry_etat.set(item["etat"])
            entry_id_salle.delete(0, tk.END)
            entry_id_salle.insert(0, item["id_salle"])
            entry_id_type_equipement.set(item["id_type_equipement"])

        tk.Button(win, text="Charger", command=load_data).grid(row=0, column=2, padx=5)

        def validate():
            id_to_edit = entry_id.get().strip()
            if not id_to_edit.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre.")
                return

            nom = entry_nom.get().strip()
            numSerie = entry_numSerie.get().strip()
            dateFinGarantie = entry_dateFinGarantie.get().strip()
            etat = entry_etat.get().strip()
            id_salle = entry_id_salle.get().strip()
            id_type_equipement = entry_id_type_equipement.get().strip()

            if not nom:
                messagebox.showerror("Erreur", "Le nom est obligatoire.")
                return
            
            if not numSerie:
                messagebox.showerror("Erreur", "Le numéro de série est obligatoire.")
                return
            
            if not dateFinGarantie:
                messagebox.showerror("Erreur", "La date de fin de garantie est obligatoire.")
                return

            is_valid, error_msg = validate_date(dateFinGarantie)
            if not is_valid:
                messagebox.showerror("Erreur", error_msg)
                return

            if etat not in etat_options:
                messagebox.showerror("Erreur", "Choisir un état valide.")
                return
            
            if not id_salle:
                messagebox.showerror("Erreur", "L'ID de salle est obligatoire.")
                return
            
            if not id_salle.isdigit():
                messagebox.showerror("Erreur", "L'ID de salle doit être un nombre.")
                return

            if id_type_equipement not in type_options:
                messagebox.showerror("Erreur", "Choisir un type d'équipement valide.")
                return

            self.db.execute("""
                UPDATE equipement
                SET nom = %s, numSerie = %s, dateFinGarantie = %s, etat = %s, id_salle = %s, id_type_equipement = %s
                WHERE id = %s
            """, (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement, id_to_edit))

            self.load_equipements()
            win.destroy()

        tk.Button(win, text="Modifier", command=validate).grid(row=7, column=0, columnspan=3, pady=10)



    def delete_equipment(self):
        """Ouvre une fenêtre pour supprimer un équipement."""
        win= tk.Toplevel(self)
        win.title("Supprimer un équipement")
        tk.Label(win, text="ID de l'équipement à supprimer :").grid(row=0, column=0, padx=10, pady=5)
        entry_id = tk.Entry(win)
        entry_id.grid(row=0, column=1, padx=10, pady=5)
        def validate():
            id_to_delete = entry_id.get().strip()
            if not id_to_delete.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre.")
                return
            self.db.execute("DELETE FROM equipement WHERE id = %s", (id_to_delete,))
            self.load_equipements()
            win.destroy()
        tk.Button(win, text="Supprimer", command=validate).grid(row=1, column=0, columnspan=2, pady=10)

    def show_interventions(self):
        """Ouvre la fenêtre de gestion des interventions pour un équipement."""
        win = tk.Toplevel(self)
        win.title("Historique des interventions")
        win.geometry("800x500")

        # Sélection de l'équipement
        top_frame = tk.Frame(win)
        top_frame.pack(pady=10)
        tk.Label(top_frame, text="ID équipement :").grid(row=0, column=0, padx=5)
        entry_id_eq = tk.Entry(top_frame, width=10)
        entry_id_eq.grid(row=0, column=1, padx=5)

        # Tableau des interventions
        columns = ("id", "date_intervention", "type_action", "description", "technicien")
        tree_int = ttk.Treeview(win, columns=columns, show="headings")
        for col, text in [("id", "ID"), ("date_intervention", "Date"), ("type_action", "Type"),
                          ("description", "Description"), ("technicien", "Technicien")]:
            tree_int.heading(col, text=text)
        tree_int.column("id", width=40)
        tree_int.column("date_intervention", width=100)
        tree_int.column("type_action", width=130)
        tree_int.column("description", width=300)
        tree_int.column("technicien", width=120)
        tree_int.pack(fill="both", expand=True, padx=10, pady=5)

        def load_interventions():
            """Charge les interventions de l'équipement sélectionné."""
            id_eq = entry_id_eq.get().strip()
            if not id_eq.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre.")
                return
            for row in tree_int.get_children():
                tree_int.delete(row)
            try:
                cursor = self.db.conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM intervention WHERE id_equipement = %s ORDER BY date_intervention DESC",
                    (id_eq,)
                )
                for item in cursor.fetchall():
                    tree_int.insert("", tk.END, values=(
                        item["id"], item["date_intervention"],
                        item["type_action"], item["description"], item["technicien"]
                    ))
            except Error as err:
                messagebox.showerror("Erreur SQL", str(err))

        tk.Button(top_frame, text="Charger", command=load_interventions).grid(row=0, column=2, padx=5)

        # Boutons d'action
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=5)

        def add_intervention():
            """Ouvre un formulaire pour ajouter une intervention."""
            id_eq = entry_id_eq.get().strip()
            if not id_eq.isdigit():
                messagebox.showerror("Erreur", "Veuillez charger un équipement d'abord.")
                return
            form = tk.Toplevel(win)
            form.title("Ajouter une intervention")

            tk.Label(form, text="Date (YYYY-MM-DD) :").grid(row=0, column=0, padx=10, pady=5)
            entry_date = tk.Entry(form)
            entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
            entry_date.grid(row=0, column=1, padx=10, pady=5)

            tk.Label(form, text="Type d'action :").grid(row=1, column=0, padx=10, pady=5)
            type_options = ["Maintenance préventive", "Réparation", "Mise à jour logicielle",
                            "Changement de composant", "Installation", "Autre"]
            entry_type = ttk.Combobox(form, values=type_options, state='readonly', width=25)
            entry_type.current(0)
            entry_type.grid(row=1, column=1, padx=10, pady=5)

            tk.Label(form, text="Description :").grid(row=2, column=0, padx=10, pady=5)
            entry_desc = tk.Text(form, width=30, height=4)
            entry_desc.grid(row=2, column=1, padx=10, pady=5)

            tk.Label(form, text="Technicien :").grid(row=3, column=0, padx=10, pady=5)
            entry_tech = tk.Entry(form)
            entry_tech.grid(row=3, column=1, padx=10, pady=5)

            def save():
                date = entry_date.get().strip()
                type_action = entry_type.get().strip()
                description = entry_desc.get("1.0", tk.END).strip()
                technicien = entry_tech.get().strip()

                if not date or not type_action or not description or not technicien:
                    messagebox.showerror("Erreur", "Tous les champs sont obligatoires.")
                    return
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Erreur", "Date invalide. Format attendu : YYYY-MM-DD.")
                    return

                self.db.execute("""
                    INSERT INTO intervention (id_equipement, date_intervention, type_action, description, technicien)
                    VALUES (%s, %s, %s, %s, %s)
                """, (id_eq, date, type_action, description, technicien))
                load_interventions()
                form.destroy()

            tk.Button(form, text="Enregistrer", command=save).grid(row=4, column=0, columnspan=2, pady=10)

        def delete_intervention():
            """Supprime l'intervention sélectionnée dans le tableau."""
            selected = tree_int.selection()
            if not selected:
                messagebox.showwarning("Attention", "Sélectionnez une intervention à supprimer.")
                return
            id_int = tree_int.item(selected[0])["values"][0]
            if messagebox.askyesno("Confirmation", f"Supprimer l'intervention #{id_int} ?"):
                self.db.execute("DELETE FROM intervention WHERE id = %s", (id_int,))
                load_interventions()

        tk.Button(btn_frame, text="Ajouter une intervention", width=22,
                  command=add_intervention).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Supprimer l'intervention", width=22,
                  command=delete_intervention).grid(row=0, column=1, padx=5)


if __name__ == "__main__":
    app = Application()
    app.mainloop()
