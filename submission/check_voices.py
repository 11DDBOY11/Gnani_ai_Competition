import asyncio
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    en_in_voices = [v for v in voices if v['Locale'].lower() == 'en-in']
    print("Found en-IN voices:")
    for v in en_in_voices:
        print(f"Name: {v['ShortName']}, Gender: {v['Gender']}, Friendly: {v['FriendlyName']}")
        
    print("\nAll IN voices:")
    all_in = [v for v in voices if 'IN' in v['Locale']]
    for v in all_in:
        print(f"Name: {v['ShortName']}, Locale: {v['Locale']}, Gender: {v['Gender']}")

if __name__ == '__main__':
    asyncio.run(main())

