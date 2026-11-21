#include <unity.h>

#include "scan_policy.h"
#include "proximity_policy.h"
#include "detection_sequence.h"

void setUp() {}
void tearDown() {}

void test_retry_delay_is_bounded() {
  TEST_ASSERT_EQUAL_UINT32(6000, scan_policy::retryDelay(3000, 60000));
  TEST_ASSERT_EQUAL_UINT32(60000, scan_policy::retryDelay(48000, 60000));
  TEST_ASSERT_EQUAL_UINT32(60000, scan_policy::retryDelay(UINT32_MAX, 60000));
}

void test_scan_timer_survives_millis_wraparound() {
  TEST_ASSERT_TRUE(scan_policy::elapsed(100, UINT32_MAX - 50, 150));
  TEST_ASSERT_FALSE(scan_policy::elapsed(100, UINT32_MAX - 50, 152));
}

void test_camera_identifier_is_query_encoded() {
  TEST_ASSERT_EQUAL_STRING("door%20%26%20gate%2F1", scan_policy::urlEncode("door & gate/1").c_str());
  TEST_ASSERT_EQUAL_STRING("front-door_1", scan_policy::urlEncode("front-door_1").c_str());
}

void test_courier_matches_the_detection_api_contract() {
  TEST_ASSERT_TRUE(scan_policy::validCourier("jne"));
  TEST_ASSERT_TRUE(scan_policy::validCourier("courier_1"));
  TEST_ASSERT_FALSE(scan_policy::validCourier("JNE"));
  TEST_ASSERT_FALSE(scan_policy::validCourier("a"));
  TEST_ASSERT_FALSE(scan_policy::validCourier("jne&camera_id=other"));
}

void test_proximity_triggers_once_and_rearms_after_clear() {
  ProximityPolicy sensor(30.0f, 40.0f);
  TEST_ASSERT_FALSE(sensor.update(20));
  TEST_ASSERT_TRUE(sensor.update(20));
  TEST_ASSERT_FALSE(sensor.update(20));
  TEST_ASSERT_FALSE(sensor.update(50));
  TEST_ASSERT_FALSE(sensor.update(50));
  TEST_ASSERT_FALSE(sensor.update(50));
  TEST_ASSERT_FALSE(sensor.update(20));
  TEST_ASSERT_TRUE(sensor.update(20));
}

void test_proximity_rejects_invalid_noise() {
  ProximityPolicy sensor(30.0f, 40.0f);
  TEST_ASSERT_FALSE(sensor.update(0));
  TEST_ASSERT_FALSE(sensor.update(20));
  TEST_ASSERT_FALSE(sensor.update(35));
  TEST_ASSERT_FALSE(sensor.update(20));
  TEST_ASSERT_TRUE(sensor.update(20));
}

void test_detection_sequence_timing() {
  DetectionSequence sequence;
  sequence.start(100);
  TEST_ASSERT_TRUE(sequence.red(100));
  TEST_ASSERT_TRUE(sequence.beep(100));
  TEST_ASSERT_FALSE(sequence.beep(300));
  TEST_ASSERT_TRUE(sequence.red(3099));
  TEST_ASSERT_FALSE(sequence.red(3100));
  TEST_ASSERT_TRUE(sequence.beep(3100));
  TEST_ASSERT_FALSE(sequence.beep(3300));
  TEST_ASSERT_TRUE(sequence.beep(3500));
  TEST_ASSERT_FALSE(sequence.finishIfDue(3699));
  TEST_ASSERT_TRUE(sequence.finishIfDue(3700));
  TEST_ASSERT_FALSE(sequence.active());
}

void test_detection_sequence_survives_timer_rollover() {
  DetectionSequence sequence;
  sequence.start(UINT32_MAX - 100);
  TEST_ASSERT_TRUE(sequence.red(50));
  TEST_ASSERT_TRUE(sequence.beep(50));
  TEST_ASSERT_TRUE(sequence.finishIfDue(3500));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_retry_delay_is_bounded);
  RUN_TEST(test_scan_timer_survives_millis_wraparound);
  RUN_TEST(test_camera_identifier_is_query_encoded);
  RUN_TEST(test_courier_matches_the_detection_api_contract);
  RUN_TEST(test_proximity_triggers_once_and_rearms_after_clear);
  RUN_TEST(test_proximity_rejects_invalid_noise);
  RUN_TEST(test_detection_sequence_timing);
  RUN_TEST(test_detection_sequence_survives_timer_rollover);
  return UNITY_END();
}
