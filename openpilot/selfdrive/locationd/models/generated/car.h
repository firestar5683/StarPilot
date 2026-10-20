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
void car_err_fun(double *nom_x, double *delta_x, double *out_2647061973780188217);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2674623342919626392);
void car_H_mod_fun(double *state, double *out_7441023162408258001);
void car_f_fun(double *state, double dt, double *out_7582243939014016185);
void car_F_fun(double *state, double dt, double *out_4968429326776778080);
void car_h_25(double *state, double *unused, double *out_3424118357067698509);
void car_H_25(double *state, double *unused, double *out_4347004889615861493);
void car_h_24(double *state, double *unused, double *out_1209077948684966761);
void car_H_24(double *state, double *unused, double *out_2933976641577452656);
void car_h_30(double *state, double *unused, double *out_4457154293686350676);
void car_H_30(double *state, double *unused, double *out_1828671931108612866);
void car_h_26(double *state, double *unused, double *out_1458476460047511660);
void car_H_26(double *state, double *unused, double *out_8088508208489917717);
void car_h_27(double *state, double *unused, double *out_4972164798077654358);
void car_H_27(double *state, double *unused, double *out_4003435242909037777);
void car_h_29(double *state, double *unused, double *out_1798670428272696578);
void car_H_29(double *state, double *unused, double *out_1318440586794220682);
void car_h_28(double *state, double *unused, double *out_7680074346326341526);
void car_H_28(double *state, double *unused, double *out_6400839603863751256);
void car_h_31(double *state, double *unused, double *out_5215759119650843375);
void car_H_31(double *state, double *unused, double *out_8714716310723269193);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}