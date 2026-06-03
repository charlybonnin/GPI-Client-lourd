# --- Importation des bibliothèques nécessaires ---
import tkinter as tk                          # Bibliothèque principale pour l'interface graphique
from tkinter import ttk, messagebox, filedialog  # Widgets avancés, boîtes de dialogue et sélecteur de fichiers
import mysql.connector                        # Connecteur Python pour MySQL/MariaDB
from mysql.connector import Error             # Classe d'erreur spécifique à MySQL
import os                                     # Gestion du système de fichiers
import csv                                    # Lecture et écriture de fichiers CSV
import json                                   # Lecture et écriture de fichiers JSON
import webbrowser                             # Ouvre un fichier dans le navigateur par défaut
from datetime import datetime                 # Manipulation des dates et heures


def valider_date(chaine_date):
    """Vérifie que la date saisie est au format YYYY-MM-DD et dans le futur."""
    try:
        objet_date = datetime.strptime(chaine_date, "%Y-%m-%d")  # Convertit la chaîne en objet date
        if objet_date <= datetime.now():                          # Vérifie que la date est dans le futur
            return False, "La date de fin de garantie doit être dans le futur."
        return True, ""   # Date valide
    except ValueError:
        # La chaîne ne correspond pas au format attendu
        return False, "La date de fin de garantie doit être au format YYYY-MM-DD."


class GestionBDD:
    """Classe qui gère la connexion et les opérations sur la base de données MySQL."""

    def __init__(self, hote="localhost", port=3306, utilisateur="root", mot_de_passe="root", nom_base="gestion_de_parc"):
        """Initialise la connexion à la base de données avec les paramètres fournis."""
        self.connexion = None       # Objet de connexion MySQL (None = non connecté)
        self.curseur = None         # Curseur SQL pour exécuter les requêtes
        self.hote = hote            # Adresse du serveur MySQL
        self.port = port            # Port du serveur MySQL (3306 par défaut)
        self.utilisateur = utilisateur   # Nom d'utilisateur MySQL
        self.mot_de_passe = mot_de_passe # Mot de passe MySQL
        self.nom_base = nom_base    # Nom de la base de données

        try:
            # Tentative de connexion au serveur MySQL
            self.connexion = mysql.connector.connect(
                host=hote,
                port=port,
                user=utilisateur,
                password=mot_de_passe,
                database=nom_base
            )
            self.curseur = self.connexion.cursor(dictionary=True)  # Curseur qui retourne des dictionnaires
            self._creer_tables()    # Crée les tables si elles n'existent pas encore
        except Error as erreur:
            # Affiche un message d'erreur si la connexion échoue
            messagebox.showerror("Erreur connexion BDD", f"Impossible de se connecter : {erreur}")

    def _creer_tables(self):
        """Crée les tables 'equipement' et 'intervention' si elles n'existent pas encore."""
        # Création de la table equipement avec ses colonnes
        self.curseur.execute("""
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
        # Création de la table intervention liée à equipement
        self.curseur.execute("""
            CREATE TABLE IF NOT EXISTS intervention (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_equipement INT NOT NULL,
                date_intervention DATE NOT NULL,
                type_action VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                technicien VARCHAR(100) NOT NULL,
                statut VARCHAR(50) NOT NULL DEFAULT 'Nouveau',
                FOREIGN KEY (id_equipement) REFERENCES equipement(id) ON DELETE CASCADE
            )
        """)
        # Ajoute la colonne statut si elle n'existe pas (migration base existante)
        try:
            self.curseur.execute(
                "ALTER TABLE intervention ADD COLUMN statut VARCHAR(50) NOT NULL DEFAULT 'Nouveau'"
            )
            self.connexion.commit()
        except Error:
            pass   # La colonne existe deja, on ignore l'erreur

        self.connexion.commit()   # Valide les modifications en base

    def est_connecte(self):
        """Retourne True si la connexion à la base de données est active."""
        return self.connexion is not None and self.curseur is not None

    def recuperer(self, nom_table):
        """Récupère toutes les lignes d'une table et les retourne sous forme de liste."""
        if not self.est_connecte():
            messagebox.showerror("Erreur", "Pas connecté à la base de données.")
            return []
        try:
            self.curseur.execute(f"SELECT * FROM {nom_table}")  # Requête pour tout sélectionner
            return self.curseur.fetchall()                       # Retourne toutes les lignes
        except Error as erreur:
            messagebox.showerror("Erreur SQL", str(erreur))
            return []

    def executer(self, requete, parametres=None):
        """Exécute une requête SQL (INSERT, UPDATE, DELETE) avec des paramètres optionnels."""
        if not self.est_connecte():
            messagebox.showerror("Erreur", "Pas connecté à la base de données.")
            return
        try:
            if parametres:
                self.curseur.execute(requete, parametres)  # Requête avec paramètres (protection injection SQL)
            else:
                self.curseur.execute(requete)              # Requête sans paramètres
            self.connexion.commit()  # Valide la modification en base
        except Error as erreur:
            messagebox.showerror("Erreur SQL", str(erreur))


class Application(tk.Tk):
    """Classe principale de l'application, hérite de tk.Tk pour créer la fenêtre principale."""

    def __init__(self):
        """Initialise la fenêtre principale et démarre l'application."""
        super().__init__()                      # Initialise la fenêtre tkinter parente
        self.title("Gestion de Parc Informatique")  # Titre de la fenêtre
        self.geometry("900x560")                # Taille de la fenêtre (largeur x hauteur)
        self.bdd = GestionBDD()                 # Crée la connexion à la base de données
        self.construire_interface()             # Construit tous les widgets de l'interface
        self.update_idletasks()                 # Force la mise à jour de l'affichage
        self.charger_equipements()              # Charge les équipements au démarrage

    def construire_interface(self):
        """Construit tous les éléments visuels de la fenêtre principale."""
        # Titre principal affiché en haut de la fenêtre
        tk.Label(self, text="Liste des Équipements", font=("Arial", 18, "bold")).pack(pady=10)

        # --- Barre de recherche ---
        cadre_recherche = tk.Frame(self)        # Cadre contenant les widgets de recherche
        cadre_recherche.pack(pady=5)
        tk.Label(cadre_recherche, text="Rechercher par :").grid(row=0, column=0, padx=5)

        # Liste déroulante pour choisir le critère de recherche
        self.critere_recherche = ttk.Combobox(
            cadre_recherche,
            values=["Salle", "Type équipement", "Nom", "Numéro de série", "État"],
            state='readonly'   # L'utilisateur ne peut pas taper librement, seulement choisir
        )
        self.critere_recherche.grid(row=0, column=1, padx=5)
        self.critere_recherche.current(0)       # Sélectionne "Salle" par défaut

        tk.Label(cadre_recherche, text="Valeur :").grid(row=0, column=2, padx=5)
        self.champ_recherche = tk.Entry(cadre_recherche)   # Champ de saisie de la valeur à rechercher
        self.champ_recherche.grid(row=0, column=3, padx=5)

        # Bouton pour lancer la recherche
        tk.Button(cadre_recherche, text="Rechercher", command=self.rechercher_equipements).grid(row=0, column=4, padx=5)
        # Bouton pour réinitialiser et tout afficher
        tk.Button(cadre_recherche, text="Tout afficher", command=self.charger_equipements).grid(row=0, column=5, padx=5)

        # --- Tableau principal des équipements ---
        self.tableau = ttk.Treeview(
            self,
            columns=("id", "nom", "numSerie", "dateFinGarantie", "etat", "id_salle", "id_type_equipement"),
            show="headings",       # Affiche seulement les en-têtes (pas la colonne arborescente)
            selectmode="extended"  # Permet la sélection multiple (Ctrl+Clic, Shift+Clic)
        )
        # Définition des colonnes : nom interne, texte affiché, largeur en pixels
        for colonne, texte in [("id", "ID"), ("nom", "Nom"), ("numSerie", "Numéro de série"),
                               ("dateFinGarantie", "Fin de garantie"), ("etat", "État"),
                               ("id_salle", "Salle"), ("id_type_equipement", "Type équipement")]:
            self.tableau.heading(colonne, text=texte)   # Texte de l'en-tête
            self.tableau.column(colonne, width=120)     # Largeur de la colonne
        self.tableau.pack(fill="both", expand=True, padx=20, pady=10)  # Remplit l'espace disponible

        # --- Ligne 1 : boutons de gestion des équipements ---
        ligne1 = tk.Frame(self)   # Cadre pour regrouper les boutons
        ligne1.pack(pady=(10, 3))
        tk.Label(ligne1, text="Équipements :", font=("Arial", 9, "bold")).pack(side="left", padx=(0, 8))
        tk.Button(ligne1, text="Ajouter", width=13, command=self.ajouter_equipement).pack(side="left", padx=4)
        tk.Button(ligne1, text="Modifier", width=13, command=self.modifier_equipement).pack(side="left", padx=4)
        tk.Button(ligne1, text="Supprimer", width=13, command=self.supprimer_equipement).pack(side="left", padx=4)
        tk.Button(ligne1, text="Interventions", width=13, command=self.afficher_interventions).pack(side="left", padx=4)

        # --- Ligne 2 : boutons import/export ---
        ligne2 = tk.Frame(self)   # Cadre pour regrouper les boutons données
        ligne2.pack(pady=(3, 10))
        tk.Label(ligne2, text="Données :", font=("Arial", 9, "bold")).pack(side="left", padx=(0, 8))
        tk.Button(ligne2, text="Exporter CSV", width=13, command=self.exporter_csv).pack(side="left", padx=4)
        tk.Button(ligne2, text="Importer CSV", width=13, command=self.importer_csv).pack(side="left", padx=4)
        tk.Button(ligne2, text="Exporter JSON", width=13, command=self.exporter_json).pack(side="left", padx=4)
        tk.Button(ligne2, text="Importer JSON", width=13, command=self.importer_json).pack(side="left", padx=4)

    def rechercher_equipements(self):
        """Lance une recherche filtrée selon le critère et la valeur saisis."""
        critere = self.critere_recherche.get()    # Récupère le critère choisi (ex: "Nom")
        valeur = self.champ_recherche.get().strip()  # Récupère la valeur saisie, sans espaces

        if not valeur:
            messagebox.showwarning("Attention", "Veuillez entrer une valeur de recherche.")
            return

        # Correspondance entre les libellés affichés et les noms de colonnes SQL
        carte_criteres = {
            "Salle": "id_salle",
            "Type équipement": "id_type_equipement",
            "Nom": "nom",
            "Numéro de série": "numSerie",
            "État": "etat"
        }
        colonne = carte_criteres.get(critere)   # Récupère le nom de colonne SQL correspondant
        if not colonne:
            return

        if critere == "Salle":
            if not valeur.isdigit():            # La salle est un ID numérique
                messagebox.showerror("Erreur", "L'ID de salle doit être un nombre.")
                return
            self.charger_equipements(f"{colonne} = %s", [valeur])     # Recherche exacte
        else:
            self.charger_equipements(f"{colonne} LIKE %s", [f"%{valeur}%"])  # Recherche partielle

    def charger_equipements(self, filtre_requete=None, filtre_params=None):
        """Charge et affiche les équipements dans le tableau, avec un filtre optionnel."""
        for ligne in self.tableau.get_children():
            self.tableau.delete(ligne)   # Vide le tableau avant de le remplir

        # Construit la requête SQL avec ou sans filtre
        requete = f"SELECT * FROM equipement WHERE {filtre_requete}" if filtre_requete else "SELECT * FROM equipement"
        parametres = filtre_params or []

        try:
            curseur_local = self.bdd.connexion.cursor(dictionary=True)  # Curseur local pour cette requête
            curseur_local.execute(requete, parametres)                   # Exécute la requête
            for element in curseur_local.fetchall():                     # Parcourt chaque ligne résultat
                self.tableau.insert("", tk.END, values=(                 # Ajoute la ligne dans le tableau
                    element["id"],
                    element["nom"],
                    element["numSerie"],
                    element["dateFinGarantie"],
                    element["etat"],
                    element["id_salle"],
                    element["id_type_equipement"]
                ))
        except Error as erreur:
            messagebox.showerror("Erreur SQL", str(erreur))

    def ajouter_equipement(self):
        """Ouvre une fenêtre formulaire pour ajouter un nouvel équipement."""
        fenetre = tk.Toplevel(self)          # Crée une nouvelle fenêtre au-dessus de la principale
        fenetre.title("Ajouter un équipement")

        options_etat = ["Parfait état", "Bon état", "État médiocre", "Mauvais état"]   # États possibles
        options_type = ["Portable", "Poste de travail", "Imprimante", "NAS", "Serveur"] # Types possibles

        # Création des champs de saisie avec leurs étiquettes
        champs = {}   # Dictionnaire pour stocker les champs de saisie
        for i, (etiquette, cle) in enumerate([
            ("Nom :", "nom"),
            ("Numéro de série :", "numSerie"),
            ("Fin de garantie (YYYY-MM-DD) :", "dateFinGarantie"),
            ("ID Salle :", "id_salle")
        ]):
            tk.Label(fenetre, text=etiquette).grid(row=i, column=0, padx=10, pady=5)  # Étiquette
            champ = tk.Entry(fenetre)                                                   # Champ de saisie texte
            champ.grid(row=i, column=1, padx=10, pady=5)
            champs[cle] = champ   # Stocke le champ dans le dictionnaire

        # Liste déroulante pour l'état
        tk.Label(fenetre, text="État :").grid(row=4, column=0, padx=10, pady=5)
        champ_etat = ttk.Combobox(fenetre, values=options_etat, state='readonly')
        champ_etat.current(0)   # Sélectionne le premier état par défaut
        champ_etat.grid(row=4, column=1, padx=10, pady=5)

        # Liste déroulante pour le type d'équipement
        tk.Label(fenetre, text="Type équipement :").grid(row=5, column=0, padx=10, pady=5)
        champ_type = ttk.Combobox(fenetre, values=options_type, state='readonly')
        champ_type.current(0)   # Sélectionne le premier type par défaut
        champ_type.grid(row=5, column=1, padx=10, pady=5)

        def valider():
            """Vérifie les champs et insère l'équipement en base si tout est correct."""
            nom = champs["nom"].get().strip()
            num_serie = champs["numSerie"].get().strip()
            date_garantie = champs["dateFinGarantie"].get().strip()
            id_salle = champs["id_salle"].get().strip()
            etat = champ_etat.get().strip()
            type_eq = champ_type.get().strip()

            # Vérifications des champs obligatoires
            if not nom:
                messagebox.showerror("Erreur", "Le nom est obligatoire."); return
            if not num_serie:
                messagebox.showerror("Erreur", "Le numéro de série est obligatoire."); return
            if not date_garantie:
                messagebox.showerror("Erreur", "La date de fin de garantie est obligatoire."); return
            ok, message_erreur = valider_date(date_garantie)   # Valide le format de la date
            if not ok:
                messagebox.showerror("Erreur", message_erreur); return
            if not id_salle:
                messagebox.showerror("Erreur", "L'ID de salle est obligatoire."); return

            # Insertion de l'équipement dans la base de données
            self.bdd.executer(
                "INSERT INTO equipement (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement) VALUES (%s,%s,%s,%s,%s,%s)",
                (nom, num_serie, date_garantie, etat, id_salle, type_eq)
            )
            self.charger_equipements()   # Rafraîchit le tableau principal
            fenetre.destroy()            # Ferme la fenêtre du formulaire

        tk.Button(fenetre, text="Ajouter", command=valider).grid(row=6, column=0, columnspan=2, pady=10)

    def modifier_equipement(self):
        """Ouvre une fenêtre pour modifier un équipement existant en saisissant son ID."""
        fenetre = tk.Toplevel(self)
        fenetre.title("Modifier un équipement")

        options_etat = ["Parfait état", "Bon état", "État médiocre", "Mauvais état"]
        options_type = ["Portable", "Poste de travail", "Imprimante", "NAS", "Serveur"]

        # Champ pour saisir l'ID de l'équipement à modifier
        tk.Label(fenetre, text="ID de l'équipement :").grid(row=0, column=0, padx=10, pady=5)
        champ_id = tk.Entry(fenetre)
        champ_id.grid(row=0, column=1, padx=10, pady=5)

        # Création des champs de modification
        champs_modif = {}   # Dictionnaire des champs éditables
        for i, (etiquette, cle) in enumerate([
            ("Nom :", "nom"),
            ("Numéro de série :", "numSerie"),
            ("Fin de garantie :", "dateFinGarantie"),
            ("ID Salle :", "id_salle")
        ], start=1):
            tk.Label(fenetre, text=etiquette).grid(row=i, column=0, padx=10, pady=5)
            champ = tk.Entry(fenetre)
            champ.grid(row=i, column=1, padx=10, pady=5)
            champs_modif[cle] = champ

        tk.Label(fenetre, text="État :").grid(row=5, column=0, padx=10, pady=5)
        champ_etat = ttk.Combobox(fenetre, values=options_etat, state='readonly')
        champ_etat.grid(row=5, column=1, padx=10, pady=5)

        tk.Label(fenetre, text="Type équipement :").grid(row=6, column=0, padx=10, pady=5)
        champ_type = ttk.Combobox(fenetre, values=options_type, state='readonly')
        champ_type.grid(row=6, column=1, padx=10, pady=5)

        def charger_donnees():
            """Charge les données de l'équipement dont l'ID est saisi dans les champs."""
            valeur_id = champ_id.get().strip()
            if not valeur_id.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre."); return
            donnees = self.bdd.recuperer("equipement")   # Récupère tous les équipements
            # Cherche l'équipement correspondant à l'ID saisi
            element = next((e for e in donnees if str(e["id"]) == valeur_id), None)
            if not element:
                messagebox.showerror("Erreur", "Équipement non trouvé."); return
            # Remplit les champs avec les données existantes
            champs_modif["nom"].delete(0, tk.END);          champs_modif["nom"].insert(0, element["nom"])
            champs_modif["numSerie"].delete(0, tk.END);     champs_modif["numSerie"].insert(0, element["numSerie"])
            champs_modif["dateFinGarantie"].delete(0, tk.END); champs_modif["dateFinGarantie"].insert(0, element["dateFinGarantie"])
            champs_modif["id_salle"].delete(0, tk.END);     champs_modif["id_salle"].insert(0, element["id_salle"])
            champ_etat.set(element["etat"])                  # Sélectionne l'état actuel
            champ_type.set(element["id_type_equipement"])    # Sélectionne le type actuel

        tk.Button(fenetre, text="Charger", command=charger_donnees).grid(row=0, column=2, padx=5)

        def valider():
            """Vérifie les champs et met à jour l'équipement en base."""
            valeur_id = champ_id.get().strip()
            if not valeur_id.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre."); return
            nom = champs_modif["nom"].get().strip()
            num_serie = champs_modif["numSerie"].get().strip()
            date_garantie = champs_modif["dateFinGarantie"].get().strip()
            id_salle = champs_modif["id_salle"].get().strip()
            etat = champ_etat.get().strip()
            type_eq = champ_type.get().strip()

            if not nom:
                messagebox.showerror("Erreur", "Le nom est obligatoire."); return
            if not num_serie:
                messagebox.showerror("Erreur", "Le numéro de série est obligatoire."); return
            if not date_garantie:
                messagebox.showerror("Erreur", "La date de fin de garantie est obligatoire."); return
            ok, message_erreur = valider_date(date_garantie)
            if not ok:
                messagebox.showerror("Erreur", message_erreur); return
            if not id_salle or not id_salle.isdigit():
                messagebox.showerror("Erreur", "L'ID de salle doit être un nombre."); return

            # Mise à jour de l'équipement en base
            self.bdd.executer(
                "UPDATE equipement SET nom=%s, numSerie=%s, dateFinGarantie=%s, etat=%s, id_salle=%s, id_type_equipement=%s WHERE id=%s",
                (nom, num_serie, date_garantie, etat, id_salle, type_eq, valeur_id)
            )
            self.charger_equipements()   # Rafraîchit le tableau
            fenetre.destroy()

        tk.Button(fenetre, text="Modifier", command=valider).grid(row=7, column=0, columnspan=3, pady=10)

    def supprimer_equipement(self):
        """Supprime le ou les équipements sélectionnés dans le tableau."""
        selection = self.tableau.selection()   # Récupère les lignes sélectionnées dans le tableau
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner au moins un équipement à supprimer.")
            return

        # Récupère les noms des équipements sélectionnés pour le message de confirmation
        noms = [self.tableau.item(s)["values"][1] for s in selection]

        if len(selection) == 1:
            message = f"Supprimer l'équipement '{noms[0]}' ?"   # Message pour une seule suppression
        else:
            # Message listant tous les équipements à supprimer
            message = f"Supprimer ces {len(selection)} équipements ?\n" + "\n".join(f"- {n}" for n in noms)

        if messagebox.askyesno("Confirmation", message):
            for s in selection:
                valeur_id = self.tableau.item(s)["values"][0]   # Récupère l'ID de chaque équipement
                self.bdd.executer("DELETE FROM equipement WHERE id = %s", (valeur_id,))
            self.charger_equipements()   # Rafraîchit le tableau après suppression

    def afficher_interventions(self):
        """Ouvre la fenêtre de gestion des interventions pour un équipement donné."""
        fenetre = tk.Toplevel(self)
        fenetre.title("Historique des interventions")
        fenetre.geometry("850x520")

        # --- En-tête : saisie de l'ID de l'équipement ---
        cadre_haut = tk.Frame(fenetre)
        cadre_haut.pack(pady=10)
        tk.Label(cadre_haut, text="ID équipement :").grid(row=0, column=0, padx=5)
        champ_id_eq = tk.Entry(cadre_haut, width=10)   # Champ pour saisir l'ID de l'équipement
        champ_id_eq.grid(row=0, column=1, padx=5)

        # --- Tableau des interventions ---
        tableau_int = ttk.Treeview(
            fenetre,
            columns=("id", "date_intervention", "type_action", "description", "technicien", "statut"),
            show="headings"
        )
        # Définition des colonnes du tableau interventions
        for colonne, texte, largeur in [
            ("id", "ID", 40),
            ("date_intervention", "Date", 100),
            ("type_action", "Type", 120),
            ("description", "Description", 240),
            ("technicien", "Technicien", 120),
            ("statut", "Statut", 120)
        ]:
            tableau_int.heading(colonne, text=texte)
            tableau_int.column(colonne, width=largeur)
        tableau_int.pack(fill="both", expand=True, padx=10, pady=5)

        def charger_interventions():
            """Charge les interventions de l'équipement dont l'ID est saisi."""
            id_eq = champ_id_eq.get().strip()   # Récupère l'ID saisi
            if not id_eq.isdigit():
                messagebox.showerror("Erreur", "L'ID doit être un nombre."); return
            for ligne in tableau_int.get_children():
                tableau_int.delete(ligne)   # Vide le tableau avant de le remplir
            try:
                curseur_local = self.bdd.connexion.cursor(dictionary=True)
                # Récupère les interventions de cet équipement, triées par date décroissante
                curseur_local.execute(
                    "SELECT * FROM intervention WHERE id_equipement = %s ORDER BY date_intervention DESC",
                    (id_eq,)
                )
                for element in curseur_local.fetchall():
                    tableau_int.insert("", tk.END, values=(
                        element["id"],
                        element["date_intervention"],
                        element["type_action"],
                        element["description"],
                        element["technicien"],
                        element.get("statut", "Nouveau")   # "Nouveau" si le statut n'existe pas encore
                    ))
            except Error as erreur:
                messagebox.showerror("Erreur SQL", str(erreur))

        tk.Button(cadre_haut, text="Charger", command=charger_interventions).grid(row=0, column=2, padx=5)

        # --- Boutons d'action sur les interventions ---
        cadre_boutons = tk.Frame(fenetre)
        cadre_boutons.pack(pady=5)

        def ajouter_intervention():
            """Ouvre un formulaire pour saisir une nouvelle intervention."""
            id_eq = champ_id_eq.get().strip()
            if not id_eq.isdigit():
                messagebox.showerror("Erreur", "Veuillez charger un équipement d'abord."); return

            formulaire = tk.Toplevel(fenetre)   # Nouvelle fenêtre pour le formulaire
            formulaire.title("Ajouter une intervention")

            # Champ date (pré-rempli avec la date du jour)
            tk.Label(formulaire, text="Date (YYYY-MM-DD) :").grid(row=0, column=0, padx=10, pady=5)
            champ_date = tk.Entry(formulaire)
            champ_date.insert(0, datetime.now().strftime("%Y-%m-%d"))   # Date d'aujourd'hui par défaut
            champ_date.grid(row=0, column=1, padx=10, pady=5)

            # Liste déroulante pour le type d'action
            tk.Label(formulaire, text="Type d'action :").grid(row=1, column=0, padx=10, pady=5)
            options_type_action = ["Maintenance préventive", "Réparation", "Mise à jour logicielle",
                                   "Changement de composant", "Installation", "Autre"]
            champ_type_action = ttk.Combobox(formulaire, values=options_type_action, state='readonly', width=25)
            champ_type_action.current(0)
            champ_type_action.grid(row=1, column=1, padx=10, pady=5)

            # Zone de texte multiligne pour la description
            tk.Label(formulaire, text="Description :").grid(row=2, column=0, padx=10, pady=5)
            champ_description = tk.Text(formulaire, width=30, height=4)
            champ_description.grid(row=2, column=1, padx=10, pady=5)

            # Champ technicien
            tk.Label(formulaire, text="Technicien :").grid(row=3, column=0, padx=10, pady=5)
            champ_technicien = tk.Entry(formulaire)
            champ_technicien.grid(row=3, column=1, padx=10, pady=5)

            # Liste déroulante pour le statut de l'intervention
            tk.Label(formulaire, text="Statut :").grid(row=4, column=0, padx=10, pady=5)
            options_statut = ["Nouveau", "En cours", "En attente client", "Complété", "Autre"]
            champ_statut = ttk.Combobox(formulaire, values=options_statut, state='readonly', width=25)
            champ_statut.current(0)   # "Nouveau" par défaut
            champ_statut.grid(row=4, column=1, padx=10, pady=5)

            def enregistrer():
                """Valide les champs et insère l'intervention en base."""
                date = champ_date.get().strip()
                type_action = champ_type_action.get().strip()
                description = champ_description.get("1.0", tk.END).strip()  # Récupère tout le texte
                technicien = champ_technicien.get().strip()
                statut = champ_statut.get().strip()

                if not date or not type_action or not description or not technicien:
                    messagebox.showerror("Erreur", "Tous les champs sont obligatoires."); return
                try:
                    datetime.strptime(date, "%Y-%m-%d")   # Vérifie le format de la date
                except ValueError:
                    messagebox.showerror("Erreur", "Date invalide. Format attendu : YYYY-MM-DD."); return

                # Insertion de l'intervention en base de données
                self.bdd.executer(
                    "INSERT INTO intervention (id_equipement, date_intervention, type_action, description, technicien, statut) VALUES (%s,%s,%s,%s,%s,%s)",
                    (id_eq, date, type_action, description, technicien, statut)
                )
                charger_interventions()   # Rafraîchit le tableau des interventions
                formulaire.destroy()

            tk.Button(formulaire, text="Enregistrer", command=enregistrer).grid(row=5, column=0, columnspan=2, pady=10)

        def generer_fiche_html():
            """Genere une fiche HTML de suivi."""
            id_eq = champ_id_eq.get().strip()
            if not id_eq.isdigit():
                messagebox.showerror('Erreur', 'Veuillez charger un equipement.')
                return
            try:
                curseur_local = self.bdd.connexion.cursor(dictionary=True)

                # Recupere en une seule requete les donnees de
                # l'equipement ET de ses interventions via la cle id_equipement
                requete_join = (
                    'SELECT '
                    'e.id AS eq_id, e.nom AS eq_nom, e.numSerie AS eq_serie, '
                    'e.dateFinGarantie AS eq_garantie, e.etat AS eq_etat, '
                    'e.id_salle AS eq_salle, e.id_type_equipement AS eq_type, '
                    'i.date_intervention, i.type_action, i.description, '
                    'i.technicien, i.statut '
                    'FROM equipement e '
                    'LEFT JOIN intervention i ON i.id_equipement = e.id '
                    'WHERE e.id = %s '
                    'ORDER BY i.date_intervention DESC'
                )
                # LEFT JOIN : conserve l'equipement meme sans intervention
                curseur_local.execute(requete_join, (id_eq,))
                resultats = curseur_local.fetchall()

                if not resultats:
                    messagebox.showerror('Erreur', 'Equipement introuvable.')
                    return

                # Toutes les lignes ont les memes infos equipement
                prem = resultats[0]

                def fmt_date(val):
                    if val is None: return '—'
                    if hasattr(val, 'strftime'): return val.strftime('%d/%m/%Y')
                    return str(val)

                eq_nom      = str(prem.get('eq_nom', '—'))
                eq_serie    = str(prem.get('eq_serie', '—'))
                eq_type     = str(prem.get('eq_type', '—'))
                eq_etat     = str(prem.get('eq_etat', '—'))
                eq_salle    = str(prem.get('eq_salle', '—'))
                eq_garantie = fmt_date(prem.get('eq_garantie'))

                # Construction des lignes du tableau HTML
                lignes_tab = ''
                if prem.get('date_intervention') is not None:
                    for r in resultats:
                        lignes_tab += '<tr>'
                        lignes_tab += '<td>' + fmt_date(r.get('date_intervention')) + '</td>'
                        lignes_tab += '<td>' + str(r.get('type_action', '')) + '</td>'
                        lignes_tab += '<td>' + str(r.get('description', '')) + '</td>'
                        lignes_tab += '<td>' + str(r.get('technicien', '')) + '</td>'
                        lignes_tab += '<td>' + str(r.get('statut', '')) + '</td>'
                        lignes_tab += '</tr>'
                else:
                    lignes_tab = "<tr><td colspan='5'>Aucune intervention.</td></tr>"

                date_gen = datetime.now().strftime('%d/%m/%Y a %H:%M')

                # Construction du HTML brut sans CSS
                html  = '<html><head><meta charset="UTF-8">'
                html += '<title>Fiche - ' + eq_nom + '</title>'
                html += '</head><body>'
                html += '<h2>Fiche de suivi - ' + eq_nom + '</h2>'
                html += '<hr>'
                html += '<h3>Informations equipement</h3>'
                html += '<table border="1">'
                html += '<tr><td><b>Nom</b></td><td>' + eq_nom + '</td></tr>'
                html += '<tr><td><b>Numero de serie</b></td><td>' + eq_serie + '</td></tr>'
                html += '<tr><td><b>Type</b></td><td>' + eq_type + '</td></tr>'
                html += '<tr><td><b>Etat</b></td><td>' + eq_etat + '</td></tr>'
                html += '<tr><td><b>Salle</b></td><td>' + eq_salle + '</td></tr>'
                html += '<tr><td><b>Fin de garantie</b></td><td>' + eq_garantie + '</td></tr>'
                html += '</table>'
                html += '<h3>Historique des interventions</h3>'
                html += '<table border="1">'
                html += '<tr><th>Date</th><th>Type</th><th>Description</th><th>Technicien</th><th>Statut</th></tr>'
                html += lignes_tab
                html += '</table>'
                html += '</body></html>'

                # Boite de dialogue pour choisir l'emplacement
                nom_fich = 'fiche_' + eq_nom.replace(' ', '_') + '.html'
                chemin = filedialog.asksaveasfilename(
                    defaultextension='.html',
                    filetypes=[('Fichier HTML', '*.html')],
                    initialfile=nom_fich,
                    title='Enregistrer la fiche'
                )
                if not chemin:
                    return

                # Ecriture du fichier HTML
                with open(chemin, 'w', encoding='utf-8') as fich:
                    fich.write(html)

                # Ouverture dans le navigateur
                chemin_url = 'file:///' + chemin.replace(chr(92), '/')
                webbrowser.open(chemin_url)
                messagebox.showinfo('Fiche generee', 'Fiche ouverte dans le navigateur.')

            except Exception as erreur:
                messagebox.showerror('Erreur', str(erreur))

        def supprimer_intervention():
            """Supprime l'intervention sélectionnée dans le tableau."""
            selection = tableau_int.selection()   # Récupère la ligne sélectionnée
            if not selection:
                messagebox.showwarning("Attention", "Sélectionnez une intervention à supprimer."); return
            valeur_id = tableau_int.item(selection[0])["values"][0]   # Récupère l'ID de l'intervention
            if messagebox.askyesno("Confirmation", f"Supprimer l'intervention #{valeur_id} ?"):
                self.bdd.executer("DELETE FROM intervention WHERE id = %s", (valeur_id,))
                charger_interventions()   # Rafraîchit le tableau

        tk.Button(cadre_boutons, text="Ajouter une intervention", width=22,
                  command=ajouter_intervention).grid(row=0, column=0, padx=5)
        tk.Button(cadre_boutons, text="Supprimer l'intervention", width=22,
                  command=supprimer_intervention).grid(row=0, column=1, padx=5)
        tk.Button(cadre_boutons, text="Générer fiche HTML", width=22,
                  command=generer_fiche_html).grid(row=0, column=2, padx=5)

    def exporter_csv(self):
        """Exporte tous les équipements dans un fichier CSV choisi par l'utilisateur."""
        chemin_fichier = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv")],
            title="Exporter les équipements"
        )
        if not chemin_fichier:
            return   # L'utilisateur a annulé
        try:
            curseur_local = self.bdd.connexion.cursor(dictionary=True)
            curseur_local.execute("SELECT * FROM equipement")
            lignes = curseur_local.fetchall()   # Récupère tous les équipements
            if not lignes:
                messagebox.showinfo("Export", "Aucun équipement à exporter."); return
            with open(chemin_fichier, "w", newline="", encoding="utf-8") as fichier:
                redacteur = csv.DictWriter(fichier, fieldnames=lignes[0].keys())  # Crée le writer CSV
                redacteur.writeheader()   # Écrit la ligne d'en-têtes
                redacteur.writerows(lignes)   # Écrit toutes les lignes de données
            messagebox.showinfo("Export réussi", f"{len(lignes)} équipement(s) exporté(s) vers :\n{chemin_fichier}")
        except Exception as erreur:
            messagebox.showerror("Erreur export", str(erreur))

    def importer_csv(self):
        """Importe des équipements depuis un fichier CSV sélectionné par l'utilisateur."""
        chemin_fichier = filedialog.askopenfilename(
            filetypes=[("Fichiers CSV", "*.csv")],
            title="Importer des équipements"
        )
        if not chemin_fichier:
            return   # L'utilisateur a annulé

        colonnes_attendues = {"nom", "numSerie", "dateFinGarantie", "etat", "id_salle", "id_type_equipement"}
        nb_inseres = 0    # Compteur de lignes insérées avec succès
        nb_erreurs = 0    # Compteur de lignes ignorées à cause d'une erreur

        try:
            with open(chemin_fichier, "r", encoding="utf-8") as fichier:
                lecteur = csv.DictReader(fichier)   # Lecteur CSV qui retourne des dictionnaires
                # Vérifie que le fichier contient bien toutes les colonnes nécessaires
                if not colonnes_attendues.issubset(set(lecteur.fieldnames or [])):
                    messagebox.showerror(
                        "Erreur import",
                        "Colonnes manquantes dans le CSV.\nColonnes attendues : " + ", ".join(colonnes_attendues)
                    )
                    return
                for ligne in lecteur:
                    nom = ligne.get("nom", "").strip()
                    num_serie = ligne.get("numSerie", "").strip()
                    date_fin = ligne.get("dateFinGarantie", "").strip()
                    etat = ligne.get("etat", "").strip()
                    id_salle = ligne.get("id_salle", "").strip()
                    id_type = ligne.get("id_type_equipement", "").strip()
                    if not nom or not num_serie:   # Champs obligatoires manquants
                        nb_erreurs += 1
                        continue
                    try:
                        self.bdd.executer(
                            "INSERT INTO equipement (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement) VALUES (%s,%s,%s,%s,%s,%s)",
                            (nom, num_serie, date_fin or None, etat, id_salle or None, id_type)
                        )
                        nb_inseres += 1
                    except Exception:
                        nb_erreurs += 1   # Erreur sur cette ligne (ex: doublon numéro de série)
            self.charger_equipements()   # Rafraîchit le tableau après import
            messagebox.showinfo("Import terminé", f"{nb_inseres} équipement(s) importé(s).\n{nb_erreurs} ligne(s) ignorée(s).")
        except Exception as erreur:
            messagebox.showerror("Erreur import", str(erreur))

    def exporter_json(self):
        """Exporte tous les équipements avec leur historique d'interventions en JSON."""
        chemin_fichier = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            title="Exporter les équipements en JSON"
        )
        if not chemin_fichier:
            return
        try:
            curseur_local = self.bdd.connexion.cursor(dictionary=True)
            curseur_local.execute("SELECT * FROM equipement")
            equipements = curseur_local.fetchall()
            if not equipements:
                messagebox.showinfo("Export", "Aucun équipement à exporter."); return
            for eq in equipements:
                for cle, valeur in eq.items():
                    if hasattr(valeur, 'isoformat'):
                        eq[cle] = valeur.isoformat()   # Convertit les dates en chaîne ISO
                # Récupère l'historique des interventions pour chaque équipement
                curseur_local.execute(
                    "SELECT date_intervention, type_action, description, technicien, statut FROM intervention WHERE id_equipement = %s ORDER BY date_intervention DESC",
                    (eq["id"],)
                )
                interventions = curseur_local.fetchall()
                for interv in interventions:
                    for cle, valeur in interv.items():
                        if hasattr(valeur, 'isoformat'):
                            interv[cle] = valeur.isoformat()   # Convertit les dates en chaîne
                eq["historique"] = interventions   # Ajoute l'historique dans les données de l'équipement
            with open(chemin_fichier, "w", encoding="utf-8") as fichier:
                json.dump(equipements, fichier, ensure_ascii=False, indent=2)  # Écrit le JSON formaté
            messagebox.showinfo("Export réussi", f"{len(equipements)} équipement(s) exporté(s) vers :\n{chemin_fichier}")
        except Exception as erreur:
            messagebox.showerror("Erreur export JSON", str(erreur))

    def importer_json(self):
        """Importe des équipements depuis un fichier JSON sélectionné par l'utilisateur."""
        chemin_fichier = filedialog.askopenfilename(
            filetypes=[("Fichiers JSON", "*.json")],
            title="Importer des équipements depuis JSON"
        )
        if not chemin_fichier:
            return
        nb_inseres = 0
        nb_erreurs = 0
        try:
            with open(chemin_fichier, "r", encoding="utf-8") as fichier:
                donnees = json.load(fichier)   # Charge le contenu JSON dans une liste
            if not isinstance(donnees, list):
                messagebox.showerror("Erreur import", "Le fichier JSON doit contenir une liste d'équipements.")
                return
            for element in donnees:
                nom = str(element.get("nom", "")).strip()
                num_serie = str(element.get("numSerie", "")).strip()
                date_fin = str(element.get("dateFinGarantie", "")).strip() or None
                etat = str(element.get("etat", "")).strip()
                id_salle = element.get("id_salle")
                id_type = str(element.get("id_type_equipement", "")).strip()
                if not nom or not num_serie:
                    nb_erreurs += 1
                    continue
                try:
                    self.bdd.executer(
                        "INSERT INTO equipement (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement) VALUES (%s,%s,%s,%s,%s,%s)",
                        (nom, num_serie, date_fin, etat, id_salle, id_type)
                    )
                    nb_inseres += 1
                except Exception:
                    nb_erreurs += 1
            self.charger_equipements()
            messagebox.showinfo("Import terminé", f"{nb_inseres} équipement(s) importé(s).\n{nb_erreurs} ligne(s) ignorée(s).")
        except Exception as erreur:
            messagebox.showerror("Erreur import JSON", str(erreur))


# Point d'entrée du programme : lance l'application si le fichier est exécuté directement
if __name__ == "__main__":
    app = Application()   # Crée l'instance de l'application
    app.mainloop()        # Démarre la boucle principale d'événements tkinter
