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
void car_err_fun(double *nom_x, double *delta_x, double *out_408914854931955974);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_177131998479136517);
void car_H_mod_fun(double *state, double *out_612188567970168411);
void car_f_fun(double *state, double dt, double *out_1999864885543950499);
void car_F_fun(double *state, double dt, double *out_3889473353313594997);
void car_h_25(double *state, double *unused, double *out_4691870608107024689);
void car_H_25(double *state, double *unused, double *out_4135237206615533559);
void car_h_24(double *state, double *unused, double *out_7256933575834984536);
void car_H_24(double *state, double *unused, double *out_3151171335774219891);
void car_h_30(double *state, double *unused, double *out_6984038239252175991);
void car_H_30(double *state, double *unused, double *out_2781453134876083196);
void car_h_26(double *state, double *unused, double *out_8151782040328317728);
void car_H_26(double *state, double *unused, double *out_830711236854732958);
void car_h_27(double *state, double *unused, double *out_6382318442842705649);
void car_H_27(double *state, double *unused, double *out_606689823075658285);
void car_h_29(double *state, double *unused, double *out_205509483633589514);
void car_H_29(double *state, double *unused, double *out_3291684479190475380);
void car_h_28(double *state, double *unused, double *out_1380645175181860004);
void car_H_28(double *state, double *unused, double *out_1790714537879055194);
void car_h_31(double *state, double *unused, double *out_4534683939755895544);
void car_H_31(double *state, double *unused, double *out_4104591244738573131);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}