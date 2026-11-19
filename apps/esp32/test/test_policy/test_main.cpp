#include <unity.h>

#include "scan_policy.h"

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

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_retry_delay_is_bounded);
  RUN_TEST(test_scan_timer_survives_millis_wraparound);
  RUN_TEST(test_camera_identifier_is_query_encoded);
  RUN_TEST(test_courier_matches_the_detection_api_contract);
  return UNITY_END();
}
