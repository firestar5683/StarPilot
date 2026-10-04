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
void car_err_fun(double *nom_x, double *delta_x, double *out_3908090119423544709);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_94487865813143080);
void car_H_mod_fun(double *state, double *out_6883866144239101093);
void car_f_fun(double *state, double dt, double *out_6768278951699235134);
void car_F_fun(double *state, double dt, double *out_1909506188347403111);
void car_h_25(double *state, double *unused, double *out_6576153234371669373);
void car_H_25(double *state, double *unused, double *out_6659186104285785683);
void car_h_24(double *state, double *unused, double *out_3352365815627571869);
void car_H_24(double *state, double *unused, double *out_7055831408639645178);
void car_h_30(double *state, double *unused, double *out_8233141311083859893);
void car_H_30(double *state, double *unused, double *out_4140853145778537056);
void car_h_26(double *state, double *unused, double *out_7065397510007718156);
void car_H_26(double *state, double *unused, double *out_3354660134524985082);
void car_h_27(double *state, double *unused, double *out_858990200057031440);
void car_H_27(double *state, double *unused, double *out_1917259074594593839);
void car_h_29(double *state, double *unused, double *out_583796137772525551);
void car_H_29(double *state, double *unused, double *out_3630621801464144872);
void car_h_28(double *state, double *unused, double *out_8161553212383445002);
void car_H_28(double *state, double *unused, double *out_8713020818533675446);
void car_h_31(double *state, double *unused, double *out_6300959172087163484);
void car_H_31(double *state, double *unused, double *out_417489146226031570);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}