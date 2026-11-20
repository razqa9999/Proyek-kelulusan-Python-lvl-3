import os
import sqlite3
from datetime import datetime
import discord
from discord.ext import commands

# Masukkan langsung tokenmu di dalam tanda kutip di bawah ini:
TOKEN = "Your_Discord_bot_Token"

# ==========================================
# 1. DATA FAQ (Sesuaikan dengan file soalmu)
# ==========================================
FAQ_DATA = {
    "pengiriman": {
        "pertanyaan": "Berapa lama proses pengiriman barang?",
        "jawaban": "Pengiriman reguler memakan waktu 2-4 hari kerja, sedangkan pengiriman instan diproses di hari yang sama sebelum pukul 15.00 WIB.",
        "keywords": ["kirim", "pengiriman", "paket", "sampai", "resi", "ekspedisi"]
    },
    "pembayaran": {
        "pertanyaan": "Metode pembayaran apa saja yang tersedia?",
        "jawaban": "Kami menerima pembayaran melalui Transfer Bank (BCA, Mandiri, BRI), E-Wallet (GoPay, OVO, DANA), dan QRIS.",
        "keywords": ["bayar", "pembayaran", "transfer", "qris", "dana", "gopay", "ovo"]
    },
    "retur": {
        "pertanyaan": "Bagaimana cara mengajukan pengembalian barang (retur)?",
        "jawaban": "Retur dapat diajukan maksimal 3x24 jam setelah barang diterima dengan menyertakan video unboxing tanpa jeda.",
        "keywords": ["retur", "kembali", "rusak", "cacat", "tukar", "refund"]
    },
    "jam_operasional": {
        "pertanyaan": "Kapan jam operasional toko?",
        "jawaban": "Toko online kami buka 24 jam, sementara layanan admin membalas pesan setiap hari pukul 08.00 - 21.00 WIB.",
        "keywords": ["jam", "buka", "tutup", "operasional", "jadwal"]
    }
}

# ==========================================
# 2. PENGATURAN DATABASE SQLITE
# ==========================================
DB_NAME = "toko_support.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalated_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            department TEXT NOT NULL,
            question TEXT NOT NULL,
            status TEXT DEFAULT 'Menunggu',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_escalation(user_id: str, username: str, department: str, question: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO escalated_questions (user_id, username, department, question, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, department, question, waktu))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

# ==========================================
# 3. KOMPONEN ANTARMUKA (MENU & TOMBOL)
# ==========================================
class FAQSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=data["pertanyaan"][:100],
                value=key,
                description="Klik untuk melihat jawaban"
            )
            for key, data in FAQ_DATA.items()
        ]
        super().__init__(placeholder="Pilih Pertanyaan Umum (FAQ)...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        pilihan = FAQ_DATA[self.values[0]]
        embed = discord.Embed(
            title=f"📌 {pilihan['pertanyaan']}",
            description=pilihan["jawaban"],
            color=discord.Color.green()
        )
        embed.set_footer(text="Semua Bisa Kamu Beli • Dukungan Pelanggan")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EscalationView(discord.ui.View):
    def __init__(self, user_question: str, author_id: int):
        super().__init__(timeout=180)
        self.user_question = user_question
        self.author_id = author_id
        self.add_item(FAQSelect())

    async def handle_escalation(self, interaction: discord.Interaction, department: str, role_label: str):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Tombol ini hanya untuk pengirim pertanyaan.", ephemeral=True)
            return

        ticket_id = save_escalation(
            user_id=str(interaction.user.id),
            username=str(interaction.user),
            department=department,
            question=self.user_question
        )

        embed = discord.Embed(
            title="✅ Pertanyaan Diteruskan ke Spesialis",
            description=(
                f"Terima kasih **{interaction.user.display_name}**! Pertanyaanmu telah dicatat ke database kami.\n\n"
                f"**Nomor Tiket:** `#{ticket_id}`\n"
                f"**Departemen Tujuan:** {role_label}\n"
                f"**Pertanyaan:** {self.user_question}"
            ),
            color=discord.Color.blue()
        )
        # Nonaktifkan tombol setelah dipilih
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Hubungi Programmer (Web/Bayar)", style=discord.ButtonStyle.danger, emoji="💻")
    async def btn_programmer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_escalation(interaction, "Programmer", "Departemen Programmer (Website & Pembayaran)")

    @discord.ui.button(label="Hubungi Staf Penjualan (Produk)", style=discord.ButtonStyle.primary, emoji="🛍️")
    async def btn_penjualan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_escalation(interaction, "Staf Penjualan", "Departemen Penjualan (Masalah Produk)")

# ==========================================
# 4. KONFIGURASI UTAMA BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    init_db()
    print(f"Bot {bot.user} berhasil online dan database siap!")

@bot.command(name="bantuan")
async def bantuan(ctx):
    """Menampilkan menu bantuan utama toko"""
    embed = discord.Embed(
        title="👋 Selamat Datang di CS Semua Bisa Kamu Beli!",
        description=(
            "Ada yang bisa kami bantu hari ini?\n"
            "• **Pilih topik FAQ** pada menu di bawah ini, atau\n"
            "• **Ketik langsung pertanyaanmu** di chat ini!"
        ),
        color=discord.Color.gold()
    )
    view = EscalationView(user_question="Permintaan bantuan via menu !bantuan", author_id=ctx.author.id)
    await ctx.send(embed=embed, view=view)

@bot.command(name="tiket")
async def lihat_tiket(ctx):
    """Perintah khusus admin untuk melihat 5 pertanyaan terakhir yang masuk ke database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, department, question, created_at FROM escalated_questions ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await ctx.send("📭 Belum ada pertanyaan yang diteruskan ke spesialis.")
        return

    embed = discord.Embed(title="📋 5 Tiket Spesialis Terbaru", color=discord.Color.purple())
    for row in rows:
        embed.add_field(
            name=f"Tiket #{row[0]} • {row[2]} ({row[4]})",
            value=f"**Dari:** {row[1]}\n**Pesan:** {row[3]}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    # Abaikan pesan dari bot sendiri
    if message.author.bot:
        return

    # Jalankan command jika diawali tanda '!'
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # Abaikan pesan kosong (misal hanya lampiran tanpa teks)
    pesan = message.content.lower().strip()
    if not pesan:
        return

    # Cek kecocokan dengan FAQ
    for key, data in FAQ_DATA.items():
        if any(keyword in pesan for keyword in data["keywords"]):
            embed = discord.Embed(
                title=f"💡 {data['pertanyaan']}",
                description=f"{data['jawaban']}\n\n*Masih butuh bantuan lain? Klik tombol di bawah untuk meneruskan ke tim spesialis kami.*",
                color=discord.Color.green()
            )
            view = EscalationView(user_question=message.content, author_id=message.author.id)
            await message.reply(embed=embed, view=view)
            return

    # Jika tidak cocok dengan FAQ manapun, tawarkan menu & tombol spesialis
    embed = discord.Embed(
        title="🤔 Pertanyaan Membutuhkan Bantuan Khusus",
        description=(
            "Maaf, kami belum menemukan jawaban otomatis untuk pertanyaan tersebut.\n"
            "Silakan cek daftar **FAQ** di menu bawah, atau teruskan pertanyaanmu langsung ke **departemen spesialis** kami:"
        ),
        color=discord.Color.orange()
    )
    view = EscalationView(user_question=message.content, author_id=message.author.id)
    await message.reply(embed=embed, view=view)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN belum diatur di file .env!")
    else:
        bot.run(TOKEN)
