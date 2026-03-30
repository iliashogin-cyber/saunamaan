# saunamaan
This is a booking calendar app for saunas and other shared spaces.

Features:
- Users can create an account and log in to the application.
- Users can add, edit, and delete their own bookings.
- Head user (Property Manager) can modify availability of the spaces: add, edit, or delete bookings for any user (resident) under this housing cooperative/company.
- Users can book recurring time slots.
- Users can view a calendar of available sauna times.
- Users can search for available sauna times on a specific date.
- User pages display bookings and other details (e.g., number of apartments).
- Users can select categories for bookings
- Head users can create announcements - share updates on upcoming changes, shared space rules, and other key information for the housing cooperative.


To create database tables:
`sqlite3 saunamaan.db < schema.sq`l`
`sqlite3 saunamaan.db < init.sql`