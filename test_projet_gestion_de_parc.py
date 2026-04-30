import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from projet_gestion_de_parc import Database, validate_date

class TestDatabase(unittest.TestCase):
    """Tests pour la classe Database avec MySQL."""

    @patch('projet_gestion_de_parc.mysql.connector.connect')
    def test_connexion(self, mock_connect):
        # Mock de la connexion MySQL
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        db = Database()
        # La connexion est mockée, on vérifie que mysql.connector.connect a été appelé
        mock_connect.assert_called_once()

    @patch('projet_gestion_de_parc.mysql.connector.connect')
    def test_connexion_params(self, mock_connect):
        # Test avec les paramètres de connexion
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        db = Database(host="localhost", port=3306, user="root", password="", database="gestion_de_parc")
        
        # Vérifier les paramètres passés
        call_args = mock_connect.call_args
        assert call_args.kwargs['host'] == "localhost"
        assert call_args.kwargs['port'] == 3306
        assert call_args.kwargs['database'] == "gestion_de_parc"

    @patch('projet_gestion_de_parc.mysql.connector.connect')
    def test_is_connected(self, mock_connect):
        # Test de la méthode is_connected
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        db = Database()
        self.assertTrue(db.is_connected())

    @patch('projet_gestion_de_parc.mysql.connector.connect')
    def test_fetch(self, mock_connect):
        # Test de la méthode fetch
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1, "nom": "PC"}]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        db = Database()
        result = db.fetch("equipement")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["nom"], "PC")

    @patch('projet_gestion_de_parc.mysql.connector.connect')
    def test_execute(self, mock_connect):
        # Test de la méthode execute
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        db = Database()
        db.execute("INSERT INTO equipement (nom) VALUES ('PC')")
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestValidateDate(unittest.TestCase):
    """Tests pour la fonction validate_date."""

    def test_date_future(self):
        # Test date dans le futur
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        is_valid, msg = validate_date(future_date)
        self.assertTrue(is_valid)

    def test_date_passee(self):
        # Test date passée
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        is_valid, msg = validate_date(past_date)
        self.assertFalse(is_valid)

    def test_format_mauvais(self):
        # Test format invalide
        is_valid, msg = validate_date("25/12/2023")
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()