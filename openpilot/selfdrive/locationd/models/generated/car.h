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
void car_err_fun(double *nom_x, double *delta_x, double *out_8346173601194974305);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5160097127653636741);
void car_H_mod_fun(double *state, double *out_5363774524485386634);
void car_f_fun(double *state, double dt, double *out_1540318947581584736);
void car_F_fun(double *state, double dt, double *out_7934222883812967780);
void car_h_25(double *state, double *unused, double *out_7598930903288826977);
void car_H_25(double *state, double *unused, double *out_460082699300721794);
void car_h_24(double *state, double *unused, double *out_5154566491491640288);
void car_H_24(double *state, double *unused, double *out_6115489107290796307);
void car_h_30(double *state, double *unused, double *out_6960167479500316175);
void car_H_30(double *state, double *unused, double *out_6456607642190894961);
void car_h_26(double *state, double *unused, double *out_5087535076795386295);
void car_H_26(double *state, double *unused, double *out_2844443270460078807);
void car_h_27(double *state, double *unused, double *out_4994525582480129326);
void car_H_27(double *state, double *unused, double *out_4281844330390470050);
void car_h_29(double *state, double *unused, double *out_7296771295388762161);
void car_H_29(double *state, double *unused, double *out_6966838986505287145);
void car_h_28(double *state, double *unused, double *out_6344779448990625368);
void car_H_28(double *state, double *unused, double *out_2513917413548611557);
void car_h_31(double *state, double *unused, double *out_3644597213434738669);
void car_H_31(double *state, double *unused, double *out_6616592551211095459);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}