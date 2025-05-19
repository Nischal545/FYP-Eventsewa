from django.db import connection
import random
import string

class EventTable:
    """
    This is not a Django model but a utility class for creating and managing
    event-specific tables with unique codes.
    """
    @staticmethod
    def generate_table_name(event_name, event_code):
        """
        Generate a unique table name based on event name and code.
        Format: [sanitized_name]_[code]
        """
        # Sanitize event name (remove spaces and special characters)
        sanitized_name = ''.join(c for c in event_name if c.isalnum()).lower()
        # Truncate if too long
        if len(sanitized_name) > 20:
            sanitized_name = sanitized_name[:20]
        return f"{sanitized_name}_{event_code}"
    
    @staticmethod
    def create_table(table_name):
        """
        Create a new table for an event with the given name.
        """
        with connection.cursor() as cursor:
            # First ensure the events schema exists
            cursor.execute("CREATE SCHEMA IF NOT EXISTS events;")
            
            # Create the table with necessary fields based on user requirements
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS events.{table_name} (
                    id SERIAL PRIMARY KEY,
                    user_name VARCHAR(100) NOT NULL,
                    paid_amount DECIMAL(10, 2) NOT NULL,
                    num_individuals INTEGER NOT NULL,
                    capacity INTEGER NOT NULL,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_email VARCHAR(255) NOT NULL,
                    ticket_code VARCHAR(10) UNIQUE NOT NULL,
                    payment_status VARCHAR(20) DEFAULT 'pending',
                    description VARCHAR(255) DEFAULT '',
                    organizer_name VARCHAR(255) DEFAULT ''
                )
            """)
            print(f"Created event-specific table: events.{table_name}")
            return True
    
    @staticmethod
    def drop_table(table_name):
        """
        Drop an event table if it exists.
        """
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS events.{table_name}")
            return True
    
    @staticmethod
    def add_ticket(table_name, ticket_data):
        """
        Add a ticket to the event table.
        
        Expected ticket_data keys:
        - user_name: Name of the ticket purchaser
        - paid_amount: Amount paid for the ticket
        - num_individuals: Number of individuals for this ticket
        - capacity: Total capacity of the event
        - user_email: Email of the ticket purchaser
        - ticket_code: Unique code for the ticket (optional, will be generated if not provided)
        - description: Optional description or notes about the ticket
        - organizer_name: Name of the event organizer
        """
        try:
            # Generate ticket code if not provided
            if 'ticket_code' not in ticket_data:
                ticket_data['ticket_code'] = EventTable.generate_ticket_code()
                
            # Set default values if not provided
            if 'payment_status' not in ticket_data:
                ticket_data['payment_status'] = 'pending'
            if 'description' not in ticket_data:
                ticket_data['description'] = ''
                
            fields = ', '.join(ticket_data.keys())
            placeholders = ', '.join(['%s'] * len(ticket_data))
            values = list(ticket_data.values())
            
            with connection.cursor() as cursor:
                # Ensure the events schema exists
                cursor.execute("CREATE SCHEMA IF NOT EXISTS events;")
                
                # Check if the table exists, create it if it doesn't
                cursor.execute(f"""SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'events' AND table_name = '{table_name}'
                )""")
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    print(f"Table events.{table_name} does not exist, creating it...")
                    EventTable.create_table(table_name)
                
                # Insert the ticket data
                cursor.execute(f"""
                    INSERT INTO events.{table_name} ({fields})
                    VALUES ({placeholders})
                    RETURNING id
                """, values)
                ticket_id = cursor.fetchone()[0]
                print(f"Added ticket ID {ticket_id} to table events.{table_name}")
                return ticket_id
        except Exception as e:
            print(f"Error adding ticket to events.{table_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_tickets(table_name, **filters):
        """
        Get tickets from the event table with optional filters.
        """
        try:
            with connection.cursor() as cursor:
                # Ensure the events schema exists
                cursor.execute("CREATE SCHEMA IF NOT EXISTS events;")
                
                # Check if the table exists
                cursor.execute(f"""SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'events' AND table_name = '{table_name}'
                )""")
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    print(f"Table events.{table_name} does not exist, creating it...")
                    EventTable.create_table(table_name)
                    return []  # Return empty list as the table was just created
                
                # Build the query
                query = f"SELECT * FROM events.{table_name}"
                params = []
                
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        conditions.append(f"{key} = %s")
                        params.append(value)
                    query += " WHERE " + " AND ".join(conditions)
                
                # Execute the query
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting tickets from events.{table_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def update_ticket(table_name, ticket_id, update_data):
        """
        Update a ticket in the event table.
        """
        try:
            set_clause = ', '.join([f"{key} = %s" for key in update_data.keys()])
            values = list(update_data.values()) + [ticket_id]
            
            with connection.cursor() as cursor:
                # Ensure the events schema exists
                cursor.execute("CREATE SCHEMA IF NOT EXISTS events;")
                
                # Check if the table exists
                cursor.execute(f"""SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'events' AND table_name = '{table_name}'
                )""")
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    print(f"Table events.{table_name} does not exist, creating it...")
                    EventTable.create_table(table_name)
                    return False  # Return False as the table was just created
                
                # Update the ticket
                cursor.execute(f"""
                    UPDATE events.{table_name}
                    SET {set_clause}
                    WHERE id = %s
                """, values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating ticket in events.{table_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def generate_ticket_code():
        """
        Generate a unique ticket code.
        """
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        digits = ''.join(random.choices(string.digits, k=5))
        return f"{letters}-{digits}"
