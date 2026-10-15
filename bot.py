import json
import os
import discord
from discord.ext import commands
from discord import app_commands

# ==============================================================================
# JSON DATABASE HELPER FUNCTIONS
# ==============================================================================
FAQ_FILE = "faqs.json"

def load_faqs():
    if not os.path.exists(FAQ_FILE):
        default_faqs = {
            "payment": "We currently accept PayPal/wise, Credit/Debit cards, and Net Banking. For custom invoicing, please open a ticket!",
            "rules": "Please review our server rules in the #rules channel. Respect all members and avoid spamming.",
            "support": "You can open a support ticket by clicking the button in the #tickets channel or asking a staff member.",
        }
        save_faqs(default_faqs)
        return default_faqs
    
    with open(FAQ_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_faqs(data):
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

FAQ_DATABASE = load_faqs()

# ==============================================================================
# BOT SETUP & INITIALIZATION
# ==============================================================================
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# ==============================================================================
# TICKET SYSTEM COMPONENTS
# ==============================================================================

class TicketModal(discord.ui.Modal, title="Support Ticket Form"):
    subject = discord.ui.TextInput(label="Subject", placeholder="Brief summary of your issue...", required=True, max_length=100)
    details = discord.ui.TextInput(label="Detailed Reason", style=discord.TextStyle.paragraph, placeholder="Provide as much detail as possible...", required=True)
    urgency = discord.ui.TextInput(label="Urgency Level", placeholder="Low / Medium / High / Urgent", required=True, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Creating your ticket, please wait...", ephemeral=True)
        
        embed = discord.Embed(title=f"🎫 Ticket: {self.subject.value}", color=discord.Color.blue())
        embed.add_field(name="Submitted By", value=interaction.user.mention, inline=False)
        embed.add_field(name="Urgency", value=self.urgency.value, inline=False)
        embed.add_field(name="Details", value=self.details.value, inline=False)
        
        view = ClaimTicketView(user=interaction.user, embed_data=embed)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send("Your ticket request has been posted!", ephemeral=True)


class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())


class ClaimTicketView(discord.ui.View):
    def __init__(self, user: discord.User, embed_data: discord.Embed):
        super().__init__(timeout=None)
        self.ticket_user = user
        self.ticket_embed = embed_data

    @discord.ui.button(label="🔒 Claim Ticket", style=discord.ButtonStyle.success, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = await interaction.message.create_thread(name=f"ticket-{self.ticket_user.name}", auto_archive_duration=1440)
        
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
        await thread.send(embed=welcome_embed)
        await interaction.response.send_message(f"Ticket claimed! Private thread created: {thread.mention}", ephemeral=True)

# ==============================================================================
# EVENTS & COMMANDS
# ==============================================================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        query = message.content.lower()
        matched_answer = None

        faqs = load_faqs()
        for key, answer in faqs.items():
            if key.lower() in query:
                matched_answer = answer
                break

        if matched_answer:
            await message.reply(matched_answer)
        else:
            topics_list = ", ".join([f"`{k}`" for k in faqs.keys()])
            await message.reply(
                f"Hello! I couldn't find an exact match for your query. "
                f"Available FAQ topics are: {topics_list} — or open a ticket for custom help!"
            )

    await bot.process_commands(message)

@bot.tree.command(name="faq", description="Search or view FAQ answers")
@app_commands.describe(topic="Type the keyword of the topic (e.g. payment, rules)")
async def faq_command(interaction: discord.Interaction, topic: str):
    faqs = load_faqs()
    topic_lower = topic.lower().strip()
    
    if topic_lower in faqs:
        embed = discord.Embed(title=f"FAQ: {topic.title()}", description=faqs[topic_lower], color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ Topic `{topic}` not found in FAQ database.", ephemeral=True)

@bot.tree.command(name="addfaq", description="Add a new FAQ entry (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(topic="The new keyword/topic name", answer="The answer text for this topic")
async def add_faq(interaction: discord.Interaction, topic: str, answer: str):
    faqs = load_faqs()
    topic_clean = topic.lower().strip()
    
    if topic_clean in faqs:
        await interaction.response.send_message(f"❌ Topic `{topic_clean}` already exists! Use `/editfaq` to modify it.", ephemeral=True)
        return

    faqs[topic_clean] = answer
    save_faqs(faqs)
    await interaction.response.send_message(f"✅ Successfully created new FAQ for topic `{topic_clean}`!", ephemeral=True)

@bot.tree.command(name="editfaq", description="Edit an existing FAQ entry (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(topic="The existing topic keyword to edit", answer="The new answer text")
async def edit_faq(interaction: discord.Interaction, topic: str, answer: str):
    faqs = load_faqs()
    topic_clean = topic.lower().strip()
    
    if topic_clean in faqs:
        faqs[topic_clean] = answer
        save_faqs(faqs)
        await interaction.response.send_message(f"✏️ Successfully updated FAQ for topic `{topic_clean}`!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Topic `{topic_clean}` does not exist! Use `/addfaq` to create it first.", ephemeral=True)

@bot.tree.command(name="deletefaq", description="Delete an FAQ entry (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(topic="The topic keyword to remove")
async def delete_faq(interaction: discord.Interaction, topic: str):
    faqs = load_faqs()
    topic_clean = topic.lower().strip()
    
    if topic_clean in faqs:
        del faqs[topic_clean]
        save_faqs(faqs)
        await interaction.response.send_message(f"🗑️ Deleted FAQ topic `{topic_clean}`.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Topic `{topic_clean}` does not exist.", ephemeral=True)

@bot.tree.command(name="setticketpanel", description="Set up the Ticket Panel in current channel")
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="Need Assistance?", description="Click the button below to open a support ticket. Our team will assist you shortly!", color=discord.Color.blue())
    view = TicketOpenView()
    await interaction.response.send_message("Ticket panel initialized!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)

BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not found!")
    else:
        bot.run(BOT_TOKEN)
