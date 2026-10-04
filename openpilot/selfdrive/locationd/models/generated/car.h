#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_949748206832459961);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3637275118739236570);
void car_H_mod_fun(double *state, double *out_2022350626202111920);
void car_f_fun(double *state, double dt, double *out_311349171040061963);
void car_F_fun(double *state, double dt, double *out_7710363422868589643);
void car_h_25(double *state, double *unused, double *out_4424746055483597783);
void car_H_25(double *state, double *unused, double *out_6926042451386776760);
void car_h_24(double *state, double *unused, double *out_3903348308188753592);
void car_H_24(double *state, double *unused, double *out_6529397147032917265);
void car_h_30(double *state, double *unused, double *out_5875377448112480950);
void car_H_30(double *state, double *unused, double *out_4604011280831158101);
void car_h_26(double *state, double *unused, double *out_7504949106878727943);
void car_H_26(double *state, double *unused, double *out_3184539132512720536);
void car_h_27(double *state, double *unused, double *out_576927212177247862);
void car_H_27(double *state, double *unused, double *out_6778774592631583012);
void car_h_29(double *state, double *unused, double *out_873704180451635305);
void car_H_29(double *state, double *unused, double *out_8492137319501134045);
void car_h_28(double *state, double *unused, double *out_6858216222251452951);
void car_H_28(double *state, double *unused, double *out_4872207737138886997);
void car_h_31(double *state, double *unused, double *out_4699940117768103672);
void car_H_31(double *state, double *unused, double *out_6956688413263737188);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}