import discord
from discord import app_commands
import asyncio
import os

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Synced slash commands.")

client = MyBot()

# --- Close Ticket View ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing and deleting this ticket thread in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

# --- Claim Ticket View ---
class ClaimTicketView(discord.ui.View):
    def __init__(self, user: discord.User, embed_data: discord.Embed):
        super().__init__(timeout=None)
        self.ticket_user = user
        self.ticket_embed = embed_data

    @discord.ui.button(label="🔐 Claim Ticket", style=discord.ButtonStyle.success, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restrict claiming to staff members only (checking Manage Messages permission)
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Only staff members can claim tickets!", ephemeral=True)
            return

        # Create private thread from the message
        thread = await interaction.message.create_thread(
            name=f"ticket-{self.ticket_user.name}", 
            auto_archive_duration=1440
        )
        
        # Add the ticket creator and the staff member to the private thread
        await thread.add_user(self.ticket_user)
        await thread.add_user(interaction.user)

        # Disable the claim button so other staff know it's taken
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.message.edit(view=self)

        # Welcome message inside the thread with the Close button attached
        welcome_embed = discord.Embed(
            title="Ticket Claimed",
            description=f"Hello {self.ticket_user.mention}, your ticket has been claimed by {interaction.user.mention}. You can both chat here privately.",
            color=discord.Color.green()
        )
        
        await thread.send(embed=self.ticket_embed)
        await thread.send(embed=welcome_embed, view=CloseTicketView())
        await interaction.response.send_message(f"Ticket claimed! Private thread created: {thread.mention}", ephemeral=True)

# --- Ticket Modal (With Subject & Reason) ---
class TicketModal(discord.ui.Modal, title="Create a Support Ticket"):
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Brief summary of your issue...",
        required=True,
        max_length=100
    )
    
    reason = discord.ui.TextInput(
        label="Reason / Description",
        style=discord.TextStyle.paragraph,
        placeholder="Please describe your issue or question in detail...",
        required=True,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"Ticket: {self.subject.value}",
            description=f"**Submitted by:** {interaction.user.mention}\n\n**Reason:**\n{self.reason.value}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        await interaction.response.send_message(
            f"Ticket submitted successfully! Staff will review it shortly.", 
            ephemeral=True
        )
        
        # Post the ticket notification with the Claim button
        await interaction.channel.send(
            content=f"New ticket opened by {interaction.user.mention}",
            embed=embed,
            view=ClaimTicketView(interaction.user, embed)
        )

# --- Ticket Panel View ---
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- Bot Events & Commands ---
@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")

@client.tree.command(name="setticketpanel", description="Set up the ticket panel in a specific channel")
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel

    embed = discord.Embed(
        title="📩 Support Tickets",
        description="Need help or have questions? Click the button below to open a private ticket with our staff!",
        color=discord.Color.blue()
    )
    
    await target_channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message(
        f"✅ Ticket panel sent to {target_channel.mention}!", 
        ephemeral=True
    )

@client.tree.command(name="endticket", description="Close and delete the current ticket thread")
async def end_ticket(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("Closing and deleting this ticket thread in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass
    else:
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket thread!", ephemeral=True)

# Run the bot
TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)
