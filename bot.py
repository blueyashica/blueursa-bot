import discord
from discord import app_commands
import asyncio
import os
import json
from google import genai

# --- Local Storage Setup for FAQs and Info ---
FAQ_FILE = "faqs.json"
INFO_FILE = "info.json"

def load_data(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

faqs = load_data(FAQ_FILE, {
    "payment": "We accept Net Banking, PayPal, Wise, and Credit/Debit Cards! We operate on a strict 50% upfront structure before work begins. Open a ticket for specific details."
})

info_data = load_data(INFO_FILE, {
    "founder_name": "Yashica",
    "founder_role": "Operating & Managing Head, Freelancer, Copywriter, Author",
    "founder_age": "17 (Born January 26, 2009)",
    "founder_email": "blueyashica@gmail.com",
    "cofounder_name": "Kabilan",
    "cofounder_role": "Co-Founder & Key Executive Assisting Lead",
    "cofounder_age": "20",
    "cofounder_email": "kabilan0728@gmail.com",
    "cofounder_location": "Chennai, Tamil Nadu",
    "agency_about": "BlueUrsa helps creators and businesses grow their audience and retain it. Growth and retention bring people in and keep them there."
})

# --- Gemini AI Client Initialization ---
gemini_key = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=gemini_key) if gemini_key else None

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

# --- Close Ticket View (Mod Only) ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Only moderators can close tickets!", ephemeral=True)
            return

        await interaction.response.send_message("Closing ticket, deleting thread and receipt in 5 seconds...")
        await asyncio.sleep(5)
        
        # Delete original channel receipt if present
        try:
            parent_channel = interaction.channel.parent
            if parent_channel:
                original_msg = await parent_channel.fetch_message(interaction.channel.id)
                await original_msg.delete()
        except Exception:
            pass

        # Delete private thread
        try:
            await interaction.channel.delete()
        except Exception:
            pass

# --- Claim Ticket View (Mod Only) ---
class ClaimTicketView(discord.ui.View):
    def __init__(self, user: discord.User, embed_data: discord.Embed):
        super().__init__(timeout=None)
        self.ticket_user = user
        self.ticket_embed = embed_data

    @discord.ui.button(label="🔐 Claim Ticket", style=discord.ButtonStyle.success, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Only staff members can claim tickets!", ephemeral=True)
            return

        thread = await interaction.message.create_thread(
            name=f"ticket-{self.ticket_user.name}", 
            auto_archive_duration=1440
        )
        
        await thread.add_user(self.ticket_user)
        await thread.add_user(interaction.user)

        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.message.edit(view=self)

        welcome_embed = discord.Embed(
            title="Ticket Claimed",
            description=f"Hello {self.ticket_user.mention}, your ticket has been claimed by {interaction.user.mention}. You can both chat here privately.",
            color=discord.Color.green()
        )
        
        await thread.send(embed=self.ticket_embed)
        await thread.send(embed=welcome_embed, view=CloseTicketView())
        await interaction.response.send_message(f"Ticket claimed! Private thread created: {thread.mention}", ephemeral=True)

# --- Ticket Modal ---
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
            "Ticket submitted successfully! Staff will review it shortly.", 
            ephemeral=True
        )
        
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

# --- Bot Events & AI Mentions ---
@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Check if bot is tagged
    if client.user in message.mentions:
        content = message.content.replace(f"<@{client.user.id}>", "").strip()
        content_lower = content.lower()

        # Direct Keyword Checks for Instant Accurate Responses
        if "payment" in content_lower or "pay" in content_lower:
            await message.channel.send(f"💳 **Payment Methods:** {faqs.get('payment', 'Net Banking, PayPal, Wise, and Credit/Debit Cards! Open a ticket for more info.')}")
            return

        if "founder" in content_lower or "yashica" in content_lower:
            if "full" in content_lower or "detail" in content_lower or "email" in content_lower:
                resp = (f"👤 **Founder Full Details:**\n"
                        f"• **Name:** {info_data['founder_name']}\n"
                        f"• **Role:** {info_data['founder_role']}\n"
                        f"• **Age:** {info_data['founder_age']}\n"
                        f"• **Work Email:** {info_data['founder_email']}")
            else:
                resp = f"👤 The Operating and Managing Head of BlueUrsa is **{info_data['founder_name']}**."
            await message.channel.send(resp)
            return

        if "co-founder" in content_lower or "cofounder" in content_lower or "kabilan" in content_lower:
            if "full" in content_lower or "detail" in content_lower:
                resp = (f"🤝 **Co-Founder Full Details:**\n"
                        f"• **Name:** {info_data['cofounder_name']}\n"
                        f"• **Role:** {info_data['cofounder_role']}\n"
                        f"• **Age:** {info_data['cofounder_age']}\n"
                        f"• **Location:** {info_data['cofounder_location']}\n"
                        f"• **Email:** {info_data['cofounder_email']}")
            else:
                resp = f"🤝 The Co-Founder of BlueUrsa is **{info_data['cofounder_name']}** ({info_data['cofounder_role']})."
            await message.channel.send(resp)
            return

        # Fallback to AI Chat via Gemini
        if ai_client:
            prompt = (
                f"You are Ursa Minor, the official AI assistant for BlueUrsa agency. "
                f"Agency Info: {info_data['agency_about']}. "
                f"Founder: {info_data['founder_name']} ({info_data['founder_role']}). "
                f"Co-Founder: {info_data['cofounder_name']} ({info_data['cofounder_role']}). "
                f"Respond to this message concisely and professionally: {content}"
            )
            try:
                async with message.channel.typing():
                    response = ai_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                    )
                    await message.channel.send(response.text)
            except Exception as e:
                await message.channel.send("Hello! I am Ursa Minor, the BlueUrsa agency bot. How can I assist you today?")
        else:
            await message.channel.send("Hello! I am Ursa Minor. How can I assist you today?")

# --- Slash Commands ---
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
    await interaction.response.send_message(f"✅ Ticket panel sent to {target_channel.mention}!", ephemeral=True)

@client.tree.command(name="endticket", description="Close and delete the current ticket thread (Mods Only)")
async def end_ticket(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Only moderators can use this command!", ephemeral=True)
        return

    if isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("Closing ticket, deleting thread and receipt in 5 seconds...")
        await asyncio.sleep(5)
        
        try:
            parent_channel = interaction.channel.parent
            if parent_channel:
                original_msg = await parent_channel.fetch_message(interaction.channel.id)
                await original_msg.delete()
        except Exception:
            pass

        try:
            await interaction.channel.delete()
        except Exception:
            pass
    else:
        await interaction.response.send_message("⚠️ This command can only be used inside a ticket thread!", ephemeral=True)

@client.tree.command(name="addfaq", description="Add or update a custom FAQ entry")
@app_commands.checks.has_permissions(administrator=True)
async def add_faq(interaction: discord.Interaction, topic: str, answer: str):
    faqs[topic.lower()] = answer
    save_data(FAQ_FILE, faqs)
    await interaction.response.send_message(f"✅ FAQ updated for **{topic.lower()}**!", ephemeral=True)

@client.tree.command(name="deletefaq", description="Delete a custom FAQ entry")
@app_commands.checks.has_permissions(administrator=True)
async def delete_faq(interaction: discord.Interaction, topic: str):
    topic_key = topic.lower()
    if topic_key in faqs:
        del faqs[topic_key]
        save_data(FAQ_FILE, faqs)
        await interaction.response.send_message(f"✅ Deleted FAQ for **{topic_key}**.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ FAQ for **{topic_key}** not found.", ephemeral=True)

@client.tree.command(name="faqs", description="List all available FAQs")
async def list_faqs(interaction: discord.Interaction):
    if not faqs:
        await interaction.response.send_message("No FAQs configured yet.", ephemeral=True)
        return
    
    embed = discord.Embed(title="❓ Frequently Asked Questions", color=discord.Color.blue())
    for topic, answer in faqs.items():
        embed.add_field(name=topic.capitalize(), value=answer, inline=False)
    
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="updateaboutme", description="Update founder details")
@app_commands.checks.has_permissions(administrator=True)
async def update_about_me(interaction: discord.Interaction, role: str = None, email: str = None, age: str = None):
    if role: info_data["founder_role"] = role
    if email: info_data["founder_email"] = email
    if age: info_data["founder_age"] = age
    
    save_data(INFO_FILE, info_data)
    await interaction.response.send_message("✅ Founder details updated successfully!", ephemeral=True)

@client.tree.command(name="showmetheway", description="Displays all bot commands and usage guide")
async def show_me_the_way(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧭 Bot Command Guide - Ursa Minor",
        description="Here is the list of available commands and who can use them:",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="👥 Member Commands",
        value=(
            "• `/faqs` - View all frequently asked questions.\n"
            "• `/showmetheway` - View this command list.\n"
            "• `@Ursa Minor [question]` - Ask questions about payments, founders, or general topics."
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Moderator & Admin Commands",
        value=(
            "• `/setticketpanel [channel]` - Deploy the support panel.\n"
            "• `/endticket` - Close a ticket thread and clean up the receipt.\n"
            "• `/addfaq [topic] [answer]` - Add/update a dynamic FAQ.\n"
            "• `/deletefaq [topic]` - Delete an existing FAQ.\n"
            "• `/updateaboutme [role] [email] [age]` - Update founder information."
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# Run Bot
TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)
