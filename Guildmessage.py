from discord_webhook import DiscordWebhook,DiscordEmbed

class Guilde_message:
    def __init__(self,        
        name,
        content
    ):
        super().__init__()
        self.name = name
        self.content = content

    def replace_mentions(self):
        #you can add all your role replaces here
        out = self.content
        #mention juice roles
        out = out.replace("@commerce","<@&1007781635116253236>")
        out = out.replace("@tech","<@&585698555042201602>")
        out = out.replace("@phantasm","<@&585698551732895764>")
        out = out.replace("@tasm","<@&585698551732895764>")
        out = out.replace("@purification","<@&649087804801810456>")
        out = out.replace("@puri","<@&649087804801810456>")
        out = out.replace("@crusader","<@&585699651706028032>")
        out = out.replace("@girg","<@&585699651706028032>")
        out = out.replace("@hasi","<@&585699651706028032>")
        out = out.replace("@zeb","<@&585699651706028032>")
        out = out.replace("@memento","<@&585698549141078026>")
        out = out.replace("@sidhe","<@&585698549141078026>")
        out = out.replace("@waterpark","<@&585698549141078026>")
        out = out.replace("@dungeons","<@&623180162007171103>")
        out = out.replace("@dungeon","<@&623180162007171103>")
        out = out.replace("@magmell","<@&744028108000067664>")
        out = out.replace("@magmel","<@&744028108000067664>")
        out = out.replace("@dailies","<@&585699743988973570>")

        out = out.replace("@crom","<@&1059588498585305259>")
        out = out.replace("@crombas","<@&1059588498585305259>")
        out = out.replace("@glen","<@&1128171762467745842>")
        out = out.replace("@glenverna","<@&1128171762467745842>")
        out = out.replace("@glenberna","<@&1128171762467745842>")

        out = out.replace("@theta","<@&1268015029194592348>")

        out = out.replace("@feather","<@&684942176932855830>")
        out = out.replace("@advfeather","<@&684942176932855830>")

        out = out.replace("@blacksmith","<@&959148034443337743>")
        out = out.replace("@tailor","<@&959148561575067698>")
        out = out.replace("@enchanter","<@&587737219234660363>")
        out = out.replace("@fragmenter","<@&587781858801221652>")
        out = out.replace("@frag","<@&587781858801221652>")
        out = out.replace("@hellgate","<@&1417920847141671014>")

        out = out.replace("@poi","<@301508313160482817>")

        self.content = out

    def cleanmessage(self):
        out = self.content
        out = out.replace("@everyone","")
        out = out.replace("@here","")
        out = out.replace("&", "") 
        self.content = out
    
    def add_emotes(self, webhook: DiscordWebhook):
        #add emotes here
        if ":foxspinn:" in self.content.lower():
            embed = DiscordEmbed(title = "spin" )
            embed.set_image(url= "https://raw.githubusercontent.com/riskdoe/mabi_guild_chat_sniffer/refs/heads/rewrite/emotes/spinn.webp")
            webhook.add_embed(embed)
        if ":foxspin:" in self.content.lower():
            embed = DiscordEmbed(title = "spin" )
            embed.set_image(url= "https://raw.githubusercontent.com/riskdoe/mabi_guild_chat_sniffer/refs/heads/rewrite/emotes/spin.webp")
            webhook.add_embed(embed)

