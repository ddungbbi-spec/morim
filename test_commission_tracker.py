"""게시판·NPC 의뢰 통합 추적과 비정상 저장 진행도의 보상 검증."""

import tempfile
import unittest

from commissions import (
    accept_commission, accept_regional_commission, claim_commission,
    claim_regional_commission, commission_state, record_defeats,
    tracked_commission_state, offer_commission,
)
from test_villages_commissions import FixedChoice
from web_app import DEFAULT_PARTY_SETUP, WebGame


class CommissionTrackerTests(unittest.TestCase):
    def new_game(self):
        game = WebGame()
        game.configure_party(DEFAULT_PARTY_SETUP)
        game.advance_dialogue(1)
        game.advance_dialogue()
        return game

    def test_offered_excluded_and_same_template_keeps_both_sources(self):
        flags = {}
        offer_commission(flags, "village", FixedChoice("forest_slime_cleanup"))
        self.assertEqual(tracked_commission_state(flags), [])
        accept_commission(flags, "village")
        accept_regional_commission(flags, "village", "forest_slime_cleanup")
        record_defeats(flags, ["슬라임"])
        entries = tracked_commission_state(flags)
        self.assertEqual(len(entries), 2)
        self.assertEqual({e["source"] for e in entries}, {"regional", "random"})
        self.assertTrue(all(e["progress"] == 1 for e in entries))

    def test_ready_first_and_claimed_removed_independently(self):
        game = self.new_game()
        offer_commission(game.flags, "village", FixedChoice("forest_slime_cleanup"))
        accept_commission(game.flags, "village")
        accept_regional_commission(game.flags, "village", "forest_wolf_watch")
        accept_regional_commission(game.flags, "village", "forest_slime_cleanup")
        record_defeats(game.flags, ["슬라임", "슬라임"])
        entries = tracked_commission_state(game.flags)
        self.assertEqual([e["status"] for e in entries], ["ready", "ready", "active"])
        claim_regional_commission(game.flags, "village", "forest_slime_cleanup",
                                  game.party, game.inventory)
        entries = tracked_commission_state(game.flags)
        self.assertEqual(entries[0]["source"], "random")
        claim_commission(game.flags, "village", game.party, game.inventory)
        self.assertEqual([e["id"] for e in tracked_commission_state(game.flags)],
                         ["forest_wolf_watch"])

    def test_report_destination_persists_away_from_village_and_after_load(self):
        game = self.new_game()
        for village, cid in [("village", "forest_slime_cleanup"),
                             ("iron_village", "miner_remains")]:
            offer_commission(game.flags, village, FixedChoice(cid))
            accept_commission(game.flags, village)
        game.game_map.move_to("forest_entrance")
        entries = game.state()["tracked_commissions"]
        self.assertEqual({e["village_id"] for e in entries}, {"village", "iron_village"})
        for entry in entries:
            location = game.game_map.locations[entry["village_id"]]
            self.assertEqual(entry["village_name"], location.name)
            self.assertEqual(entry["report_to"], location.quest_npc)
        with tempfile.TemporaryDirectory() as directory:
            game.save_dir = directory
            self.assertTrue(game.save_action("save", 1)["ok"])
            game.flags = {}
            self.assertTrue(game.save_action("load", 1)["ok"])
            self.assertEqual(game.state()["tracked_commissions"], entries)

    def test_bad_progress_cannot_unlock_rewards_or_break_state(self):
        for progress in [float("inf"), float("-inf"), "invalid", None, [], -5, 1]:
            with self.subTest(progress=progress):
                game = self.new_game()
                game.flags["random_commissions"] = {"village": {
                    "template_id": "forest_slime_cleanup", "status": "ready",
                    "progress": progress,
                }}
                before = (game.party.gold, len(game.inventory))
                self.assertEqual(commission_state(game.flags, "village")["status"], "active")
                self.assertIsNone(claim_commission(game.flags, "village", game.party, game.inventory))
                self.assertEqual((game.party.gold, len(game.inventory)), before)
                self.assertEqual(len(game.state()["tracked_commissions"]), 1)

    def test_complete_progress_recovers_ready_and_offered_starts_at_zero(self):
        flags = {"random_commissions": {"village": {
            "template_id": "forest_slime_cleanup", "status": "active", "progress": 9,
        }}}
        self.assertEqual(commission_state(flags, "village")["status"], "ready")
        flags["random_commissions"]["village"]["status"] = "offered"
        self.assertEqual(commission_state(flags, "village")["progress"], 0)
        self.assertEqual(tracked_commission_state(flags), [])

    def test_invalid_template_id_ignored(self):
        flags = {"random_commissions": {"village": {
            "template_id": [], "status": "active", "progress": 0,
        }}}
        self.assertEqual(tracked_commission_state(flags), [])

    def test_invalid_status_types_do_not_break_global_tracker(self):
        for status in [[], {}, None, 3]:
            with self.subTest(status=status):
                game = self.new_game()
                game.flags["random_commissions"] = {"iron_village": {
                    "template_id": "miner_remains", "status": status, "progress": 0,
                }}
                game.flags["regional_commissions"] = {
                    "forest_slime_cleanup": {"status": status, "progress": 0},
                }
                self.assertEqual(game.state()["tracked_commissions"], [])


if __name__ == "__main__":
    unittest.main()
